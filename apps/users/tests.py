import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.users.models import Profile

User = get_user_model()


@pytest.mark.django_db
class TestSignupFlow:
    def test_signup_page_loads(self):
        client = Client()
        response = client.get(reverse('signup'))
        assert response.status_code == 200

    def test_signup_creates_user_and_profile(self):
        client = Client()
        response = client.post(reverse('signup'), {
            'username': 'newuser',
            'email': 'new@test.com',
            'team_name': 'MyTeam',
            'password1': 'strongpass123!',
            'password2': 'strongpass123!',
        })
        assert response.status_code == 302
        assert User.objects.filter(username='newuser').exists()
        user = User.objects.get(username='newuser')
        assert Profile.objects.filter(user=user).exists()
        profile = Profile.objects.get(user=user)
        assert profile.team_name == 'MyTeam'

    def test_signup_duplicate_email_rejected(self, user):
        client = Client()
        response = client.post(reverse('signup'), {
            'username': 'anotheruser',
            'email': 'test@test.com',  # Same as user fixture
            'team_name': 'UniqueTeam',
            'password1': 'strongpass123!',
            'password2': 'strongpass123!',
        })
        assert response.status_code == 200  # Re-renders form with errors
        assert not User.objects.filter(username='anotheruser').exists()

    def test_signup_duplicate_team_name_rejected(self, user):
        client = Client()
        response = client.post(reverse('signup'), {
            'username': 'anotheruser',
            'email': 'another@test.com',
            'team_name': 'TestTeam',  # Same as user fixture
            'password1': 'strongpass123!',
            'password2': 'strongpass123!',
        })
        assert response.status_code == 200
        assert not User.objects.filter(username='anotheruser').exists()

    def test_signup_password_mismatch_rejected(self):
        client = Client()
        response = client.post(reverse('signup'), {
            'username': 'newuser',
            'email': 'new@test.com',
            'team_name': 'MyTeam',
            'password1': 'strongpass123!',
            'password2': 'differentpass456!',
        })
        assert response.status_code == 200
        assert not User.objects.filter(username='newuser').exists()


@pytest.mark.django_db
class TestLoginFlow:
    def test_login_page_loads(self):
        client = Client()
        response = client.get(reverse('login'))
        assert response.status_code == 200

    def test_login_success(self, user):
        client = Client()
        response = client.post(reverse('login'), {
            'username': 'testplayer',
            'password': 'testpass123',
        })
        assert response.status_code == 302

    def test_login_wrong_password(self, user):
        client = Client()
        response = client.post(reverse('login'), {
            'username': 'testplayer',
            'password': 'wrongpassword',
        })
        assert response.status_code == 200  # Re-renders login page

    def test_logout(self, user):
        client = Client()
        client.login(username='testplayer', password='testpass123')
        response = client.get(reverse('logout'))
        assert response.status_code == 302


@pytest.mark.django_db
class TestDashboard:
    def test_dashboard_requires_login(self):
        client = Client()
        response = client.get(reverse('dashboard'))
        assert response.status_code == 302
        assert '/login' in response.url or '/users/login' in response.url

    def test_dashboard_loads_authenticated(self, user):
        client = Client()
        client.login(username='testplayer', password='testpass123')
        response = client.get(reverse('dashboard'))
        assert response.status_code == 200


@pytest.mark.django_db
class TestSchedulePage:
    def test_schedule_requires_login(self):
        client = Client()
        response = client.get(reverse('schedule'))
        assert response.status_code == 302

    def test_schedule_loads_authenticated(self, user):
        client = Client()
        client.login(username='testplayer', password='testpass123')
        response = client.get(reverse('schedule'))
        assert response.status_code == 200

    def test_schedule_week_filter(self, user, future_game):
        client = Client()
        client.login(username='testplayer', password='testpass123')
        response = client.get(reverse('schedule') + '?week=1')
        assert response.status_code == 200

    def test_schedule_season_view(self, user, future_game):
        client = Client()
        client.login(username='testplayer', password='testpass123')
        response = client.get(reverse('schedule') + '?view=season')
        assert response.status_code == 200


@pytest.mark.django_db
class TestStandingsPage:
    def test_general_standings_loads(self, user):
        client = Client()
        client.login(username='testplayer', password='testpass123')
        response = client.get(reverse('general_standings'))
        assert response.status_code == 200

    def test_standings_page_loads(self, user, league):
        client = Client()
        client.login(username='testplayer', password='testpass123')
        response = client.get(reverse('standings'))
        assert response.status_code == 200


@pytest.mark.django_db
class TestVsCPU:
    def test_vs_cpu_page_shows_optin_when_inactive(self, user):
        client = Client()
        client.login(username='testplayer', password='testpass123')
        response = client.get(reverse('vs_cpu'))
        assert response.status_code == 200
        assert b'Activate CPU Challenge' in response.content

    def test_vs_cpu_page_loads_when_active(self, user):
        user.profile.cpu_challenge_active = True
        user.profile.save()
        client = Client()
        client.login(username='testplayer', password='testpass123')
        response = client.get(reverse('vs_cpu'))
        assert response.status_code == 200
        assert b'Activate CPU Challenge' not in response.content

    def test_toggle_cpu_challenge(self, user):
        client = Client()
        client.login(username='testplayer', password='testpass123')
        response = client.post(reverse('toggle_cpu_challenge'))
        assert response.status_code == 302
        user.profile.refresh_from_db()
        assert user.profile.cpu_challenge_active is True

    def test_toggle_cpu_challenge_rejects_get(self, user):
        client = Client()
        client.login(username='testplayer', password='testpass123')
        response = client.get(reverse('toggle_cpu_challenge'))
        assert response.status_code == 302
        user.profile.refresh_from_db()
        assert user.profile.cpu_challenge_active is False

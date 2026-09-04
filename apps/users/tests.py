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
            'password1': 'strongpass123!',
            'password2': 'strongpass123!',
        })
        assert response.status_code == 302
        assert User.objects.filter(username='newuser').exists()
        user = User.objects.get(username='newuser')
        assert Profile.objects.filter(user=user).exists()
        profile = Profile.objects.get(user=user)
        # Signup no longer collects a team name; it defaults to the username
        # (via the post_save signal) and can be personalized later.
        assert profile.team_name == 'newuser'

    def test_signup_duplicate_email_rejected(self, user):
        client = Client()
        response = client.post(reverse('signup'), {
            'username': 'anotheruser',
            'email': 'test@test.com',  # Same as user fixture
            'password1': 'strongpass123!',
            'password2': 'strongpass123!',
        })
        assert response.status_code == 200  # Re-renders form with errors
        assert not User.objects.filter(username='anotheruser').exists()

    def test_signup_password_mismatch_rejected(self):
        client = Client()
        response = client.post(reverse('signup'), {
            'username': 'newuser',
            'email': 'new@test.com',
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

    def test_dashboard_shows_onboarding_without_league(self, user):
        client = Client()
        client.force_login(user)
        response = client.get(reverse('dashboard'))
        assert response.status_code == 200
        assert b'Join a league to get started' in response.content

    def test_dashboard_shows_league_snapshot(self, user, league):
        # `league`'s commissioner is `user`, who is auto-added as a member.
        client = Client()
        client.force_login(user)
        response = client.get(reverse('dashboard'))
        assert response.status_code == 200
        assert league.name.encode() in response.content
        assert b'Standings' in response.content

    def test_dashboard_shows_streak_and_badges(self, user, league):
        # `league`'s commissioner is `user`, who is auto-added as a member, so
        # the streak/badges card (gated on having a league) renders.
        client = Client()
        client.force_login(user)
        response = client.get(reverse('dashboard'))
        assert response.status_code == 200
        assert b'Current Streak' in response.content
        assert b'Badges' in response.content
        assert response.context['badges']  # list of badge dicts present
        # A brand-new user has earned nothing yet.
        assert response.context['earned_badge_count'] == 0

    def test_dashboard_switches_active_league(self, user, league):
        # Second league (alphabetically after "Test League") the user also joins.
        from apps.leagues.models import League, LeagueMembership
        other = League.objects.create(
            name='Zephyr League', commissioner=user, sport='NFL', is_approved=True,
        )
        LeagueMembership.objects.get_or_create(user=user, league=other)

        client = Client()
        client.force_login(user)

        # Default focuses the alphabetically-first league...
        default = client.get(reverse('dashboard'))
        assert default.context['primary_league'].id == league.id
        # ...and the switcher lists both leagues.
        assert b'Your leagues' in default.content
        assert b'Zephyr League' in default.content

        # Selecting the other league refocuses the dashboard on it.
        switched = client.get(reverse('dashboard'), {'league': other.id})
        assert switched.context['primary_league'].id == other.id

    def test_dashboard_ignores_league_the_user_is_not_in(self, user, league):
        from apps.leagues.models import League
        stranger_league = League.objects.create(
            name='Not Mine', commissioner=User.objects.create_user(
                username='someoneelse', password='x'),
            sport='NFL', is_approved=True,
        )
        client = Client()
        client.force_login(user)
        response = client.get(reverse('dashboard'), {'league': stranger_league.id})
        # Falls back to the user's own league rather than exposing another's.
        assert response.status_code == 200
        assert response.context['primary_league'].id == league.id


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
    def test_general_standings_redirects_to_league_standings(self, user):
        # The Overall board was retired; this route now forwards to the
        # per-league standings experience without erroring.
        client = Client()
        client.login(username='testplayer', password='testpass123')
        response = client.get(reverse('general_standings'), follow=True)
        assert response.status_code == 200

    def test_standings_page_loads(self, user, league):
        client = Client()
        client.login(username='testplayer', password='testpass123')
        response = client.get(reverse('standings'), follow=True)
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


@pytest.mark.django_db
class TestSEO:
    def test_robots_txt(self):
        response = Client().get('/robots.txt')
        assert response.status_code == 200
        assert response['Content-Type'].startswith('text/plain')
        body = response.content.decode()
        assert 'User-agent: *' in body
        assert 'Sitemap:' in body

    def test_sitemap_xml(self):
        response = Client().get('/sitemap.xml')
        assert response.status_code == 200
        assert 'xml' in response['Content-Type']
        body = response.content.decode()
        assert '<urlset' in body
        assert reverse('privacy') in body
        assert reverse('terms') in body

    def test_canonical_tag_present(self):
        body = Client().get('/').content.decode()
        assert 'rel="canonical"' in body


@pytest.mark.django_db
class TestAnalyticsFunnel:
    """Server-queued funnel events replay once, then clear. ptpTrack is always
    defined so instrumentation can call it unconditionally."""

    def test_ptptrack_always_defined(self):
        body = Client().get('/').content.decode()
        assert 'window.ptpTrack' in body

    def test_no_replay_without_queued_events(self):
        body = Client().get('/').content.decode()
        # No conversion happened, so nothing is replayed.
        assert '.forEach(function (ev)' not in body

    def test_signup_queues_and_fires_once(self):
        client = Client()
        response = client.post(reverse('signup'), {
            'username': 'funneluser',
            'email': 'funnel@test.com',
            'password1': 'strongpass123!',
            'password2': 'strongpass123!',
        }, follow=True)
        assert response.status_code == 200
        # Replayed on the page the signup redirect lands on.
        assert '"name": "signup"' in response.content.decode()
        # Exactly once: a subsequent page load no longer carries it.
        again = client.get(reverse('dashboard')).content.decode()
        assert '"name": "signup"' not in again


@pytest.mark.django_db
class TestPWA:
    """PWA-lite: installable manifest, root-scoped service worker, offline shell,
    and base-template wiring."""

    def test_manifest_served(self):
        response = Client().get('/manifest.webmanifest')
        assert response.status_code == 200
        assert 'manifest' in response['Content-Type']
        body = response.content.decode()
        assert 'PrimeTimePix' in body
        assert '"display": "standalone"' in body
        assert 'icon-512.png' in body
        assert 'maskable' in body

    def test_service_worker_served_root_scope(self):
        response = Client().get('/sw.js')
        assert response.status_code == 200
        assert 'javascript' in response['Content-Type']
        # Must be allowed to control the whole origin.
        assert response['Service-Worker-Allowed'] == '/'
        body = response.content.decode()
        # Ships with push handlers so web push lights up later.
        assert "addEventListener('push'" in body
        assert "addEventListener('install'" in body

    def test_offline_page_served(self):
        response = Client().get('/offline/')
        assert response.status_code == 200
        assert b'offline' in response.content.lower()

    def test_base_template_wires_pwa(self):
        body = Client().get('/').content.decode()
        assert 'rel="manifest"' in body
        assert "serviceWorker.register('/sw.js')" in body

    def test_dashboard_has_install_banner(self, user):
        client = Client()
        client.force_login(user)
        body = client.get(reverse('dashboard')).content.decode()
        assert 'pwa-install-banner' in body


@pytest.mark.django_db
class TestAnalyticsGating:
    """Analytics scripts render only when configured via env — dev/tests stay
    script-free."""

    def test_no_analytics_by_default(self):
        body = Client().get('/').content.decode()
        assert 'googletagmanager.com' not in body
        assert 'plausible.io' not in body

    def test_ga_renders_when_configured(self, settings):
        settings.GA_MEASUREMENT_ID = 'G-TEST123'
        body = Client().get('/').content.decode()
        assert 'googletagmanager.com/gtag/js?id=G-TEST123' in body

    def test_plausible_renders_when_configured(self, settings):
        settings.PLAUSIBLE_DOMAIN = 'primetimepixsports.com'
        body = Client().get('/').content.decode()
        assert 'plausible.io/js/script.js' in body
        assert 'data-domain="primetimepixsports.com"' in body


@pytest.mark.django_db
class TestLandingCopy:
    """The landing page must not promise a global leaderboard (retired) or show
    a fabricated live count."""

    def test_landing_loads(self):
        response = Client().get('/')
        assert response.status_code == 200

    def test_no_fabricated_stat_or_global_leaderboard(self):
        body = Client().get('/').content.decode()
        assert '284' not in body
        assert 'global rankings' not in body.lower()
        assert 'global leaderboard' not in body.lower()

    def test_footer_standings_link_wired(self):
        # Footer "Standings" link points at the real standings route, not '#'.
        body = Client().get('/').content.decode()
        assert reverse('standings') in body


@pytest.mark.django_db
class TestLegalPages:
    """Privacy / Terms must be reachable and linked — required for trust and
    for sending marketing email/ads."""

    def test_privacy_page_loads(self):
        response = Client().get(reverse('privacy'))
        assert response.status_code == 200
        assert b'Privacy Policy' in response.content

    def test_terms_page_loads(self):
        response = Client().get(reverse('terms'))
        assert response.status_code == 200
        assert b'Terms of Service' in response.content

    def test_footer_links_to_legal_pages(self):
        # The base template footer should point at the real pages, not '#'.
        response = Client().get(reverse('privacy'))
        assert reverse('privacy').encode() in response.content
        assert reverse('terms').encode() in response.content


@pytest.mark.django_db
class TestUnsubscribe:
    """Token-based, login-free unsubscribe wired to the profile email toggle."""

    def test_token_round_trips(self, user):
        from apps.users.unsubscribe import make_token, read_token
        token = make_token(user)
        assert read_token(token) == user.pk

    def test_unsubscribe_url_points_at_route(self, user):
        from apps.users.unsubscribe import unsubscribe_url
        url = unsubscribe_url(user)
        assert '/unsubscribe/' in url

    def test_token_link_unsubscribes_without_login(self, user):
        from apps.users.unsubscribe import make_token
        assert user.profile.email_reminders_enabled is True
        # No login — simulates clicking the link from an inbox.
        response = Client().get(reverse('unsubscribe', args=[make_token(user)]))
        assert response.status_code == 200
        assert b'unsubscribed' in response.content.lower()
        user.profile.refresh_from_db()
        assert user.profile.email_reminders_enabled is False

    def test_resubscribe_via_same_link(self, user):
        from apps.users.unsubscribe import make_token
        user.profile.email_reminders_enabled = False
        user.profile.save()
        token = make_token(user)
        response = Client().get(
            reverse('unsubscribe', args=[token]) + '?resubscribe=1'
        )
        assert response.status_code == 200
        user.profile.refresh_from_db()
        assert user.profile.email_reminders_enabled is True

    def test_tampered_token_is_rejected(self, user):
        response = Client().get(reverse('unsubscribe', args=['not-a-real-token']))
        assert response.status_code == 200
        assert b'invalid' in response.content.lower()
        # Nobody's preferences were touched.
        user.profile.refresh_from_db()
        assert user.profile.email_reminders_enabled is True

    def test_logged_in_fallback_without_token(self, user):
        client = Client()
        client.login(username='testplayer', password='testpass123')
        response = client.get(reverse('unsubscribe_self'))
        assert response.status_code == 200
        user.profile.refresh_from_db()
        assert user.profile.email_reminders_enabled is False

    def test_reminder_email_includes_unsubscribe_link(self, user, monkeypatch):
        # A sent pick reminder must carry a working unsubscribe link (CAN-SPAM).
        from django.core import mail
        from django.template.loader import render_to_string
        from apps.users.unsubscribe import unsubscribe_url
        html = render_to_string('emails/pick_reminder.html', {
            'username': user.username,
            'headline': 'Test',
            'body_text': 'test',
            'week': 1,
            'matchup_away': 'A',
            'matchup_home': 'B',
            'primetime_label': 'SNF',
            'game_day': 'Sunday',
            'game_time': '8:20 PM ET',
            'site_url': 'https://example.com',
            'unsubscribe_url': unsubscribe_url(user),
        })
        assert '/unsubscribe/' in html
        assert 'Unsubscribe' in html

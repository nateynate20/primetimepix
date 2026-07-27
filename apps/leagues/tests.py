import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.users.models import Profile
from apps.leagues.models import League, LeagueMembership, LeagueJoinRequest
from apps.leagues.admin import LeagueAdminForm

User = get_user_model()


def make_user(username, team_name):
    u = User.objects.create_user(
        username=username, password='testpass123', email=f'{username}@test.com'
    )
    Profile.objects.get_or_create(user=u, defaults={'team_name': team_name})
    return u


@pytest.fixture
def co_commissioner(db, league):
    """A member of `league` who has been made a co-commissioner."""
    cc = make_user('cochief', 'CoTeam')
    LeagueMembership.objects.get_or_create(user=cc, league=league)
    league.co_commissioners.add(cc)
    return cc


@pytest.fixture
def plain_member(db, league):
    """A member of `league` with no special role."""
    m = make_user('plainmember', 'PlainTeam')
    LeagueMembership.objects.get_or_create(user=m, league=league)
    return m


@pytest.fixture
def outsider(db):
    """A user who is not part of the league at all."""
    return make_user('outsider', 'OutTeam')


# ---------------------------------------------------------------------------
# Model helpers
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestLeagueCommissionerHelpers:
    def test_is_commissioner_true_for_primary(self, league):
        assert league.is_commissioner(league.commissioner) is True

    def test_is_commissioner_true_for_co(self, league, co_commissioner):
        assert league.is_commissioner(co_commissioner) is True

    def test_is_commissioner_false_for_member(self, league, plain_member):
        assert league.is_commissioner(plain_member) is False

    def test_all_commissioners_includes_both(self, league, co_commissioner):
        names = {u.username for u in league.all_commissioners()}
        assert names == {league.commissioner.username, 'cochief'}

    def test_regenerate_invite_changes_code(self, league):
        old = league.invite_code
        new = league.regenerate_invite_code()
        assert new != old
        league.refresh_from_db()
        assert league.invite_code == new

    def test_leagues_have_unique_invite_codes(self, league):
        other = League.objects.create(
            name='Another League', commissioner=league.commissioner,
            sport='NFL', is_approved=True,
        )
        assert other.invite_code != league.invite_code


# ---------------------------------------------------------------------------
# Manage League page access control
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestManageLeagueAccess:
    def test_primary_commissioner_can_open(self, league):
        client = Client()
        client.force_login(league.commissioner)
        response = client.get(reverse('manage_league', args=[league.id]))
        assert response.status_code == 200

    def test_co_commissioner_can_open(self, league, co_commissioner):
        client = Client()
        client.force_login(co_commissioner)
        response = client.get(reverse('manage_league', args=[league.id]))
        assert response.status_code == 200

    def test_plain_member_blocked(self, league, plain_member):
        client = Client()
        client.force_login(plain_member)
        response = client.get(reverse('manage_league', args=[league.id]))
        assert response.status_code == 404

    def test_outsider_blocked(self, league, outsider):
        client = Client()
        client.force_login(outsider)
        response = client.get(reverse('manage_league', args=[league.id]))
        assert response.status_code == 404

    def test_anonymous_redirected_to_login(self, league):
        client = Client()
        response = client.get(reverse('manage_league', args=[league.id]))
        assert response.status_code == 302
        assert '/login' in response.url or '/users/login' in response.url


# ---------------------------------------------------------------------------
# Editing league details
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestEditLeague:
    def test_co_commissioner_can_edit(self, league, co_commissioner):
        client = Client()
        client.force_login(co_commissioner)
        response = client.post(reverse('manage_league', args=[league.id]), {
            'name': 'Renamed League',
            'description': 'Updated by co-commissioner',
        })
        assert response.status_code == 302
        league.refresh_from_db()
        assert league.name == 'Renamed League'
        assert league.description == 'Updated by co-commissioner'

    def test_member_cannot_edit(self, league, plain_member):
        client = Client()
        client.force_login(plain_member)
        response = client.post(reverse('manage_league', args=[league.id]), {
            'name': 'Hacked Name',
            'description': 'nope',
        })
        assert response.status_code == 404
        league.refresh_from_db()
        assert league.name != 'Hacked Name'


# ---------------------------------------------------------------------------
# Invite links
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestInviteLinks:
    def test_authenticated_user_joins_via_invite(self, league, outsider):
        client = Client()
        client.force_login(outsider)
        response = client.get(reverse('join_via_invite', args=[league.invite_code]))
        assert response.status_code == 302
        assert LeagueMembership.objects.filter(user=outsider, league=league).exists()

    def test_anonymous_visitor_routed_to_signup(self, league):
        client = Client()
        response = client.get(reverse('join_via_invite', args=[league.invite_code]))
        assert response.status_code == 302
        assert reverse('signup') in response.url
        assert 'next=' in response.url

    def test_regenerate_invalidates_old_link(self, league, outsider):
        old_code = league.invite_code
        client = Client()
        client.force_login(league.commissioner)
        response = client.post(reverse('regenerate_invite', args=[league.id]))
        assert response.status_code == 302
        league.refresh_from_db()
        assert league.invite_code != old_code

        # Old link no longer resolves to any league.
        other = Client()
        other.force_login(outsider)
        stale = other.get(reverse('join_via_invite', args=[old_code]))
        assert stale.status_code == 404

    def test_member_cannot_regenerate(self, league, plain_member):
        client = Client()
        client.force_login(plain_member)
        response = client.post(reverse('regenerate_invite', args=[league.id]))
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Removing members
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestRemoveMember:
    def test_co_commissioner_removes_member(self, league, co_commissioner, plain_member):
        client = Client()
        client.force_login(co_commissioner)
        response = client.post(
            reverse('remove_member', args=[league.id, plain_member.id])
        )
        assert response.status_code == 302
        assert not LeagueMembership.objects.filter(
            user=plain_member, league=league
        ).exists()

    def test_cannot_remove_primary_commissioner(self, league, co_commissioner):
        client = Client()
        client.force_login(co_commissioner)
        response = client.post(
            reverse('remove_member', args=[league.id, league.commissioner.id])
        )
        assert response.status_code == 302
        assert LeagueMembership.objects.filter(
            user=league.commissioner, league=league
        ).exists()

    def test_removing_member_revokes_co_commissioner(self, league, co_commissioner):
        client = Client()
        client.force_login(league.commissioner)
        client.post(reverse('remove_member', args=[league.id, co_commissioner.id]))
        league.refresh_from_db()
        assert not league.co_commissioners.filter(id=co_commissioner.id).exists()

    def test_member_cannot_remove_others(self, league, plain_member):
        other = make_user('another', 'AnotherTeam')
        LeagueMembership.objects.create(user=other, league=league)
        client = Client()
        client.force_login(plain_member)
        response = client.post(reverse('remove_member', args=[league.id, other.id]))
        assert response.status_code == 404
        assert LeagueMembership.objects.filter(user=other, league=league).exists()


# ---------------------------------------------------------------------------
# Join request approval by co-commissioner
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestCoCommissionerApprovesRequests:
    def test_co_commissioner_can_approve(self, league, co_commissioner, outsider):
        join_request = LeagueJoinRequest.objects.create(user=outsider, league=league)
        client = Client()
        client.force_login(co_commissioner)
        response = client.post(reverse('approve_join_request', args=[join_request.id]))
        assert response.status_code == 302
        assert LeagueMembership.objects.filter(user=outsider, league=league).exists()

    def test_member_cannot_approve(self, league, plain_member, outsider):
        join_request = LeagueJoinRequest.objects.create(user=outsider, league=league)
        client = Client()
        client.force_login(plain_member)
        response = client.post(reverse('approve_join_request', args=[join_request.id]))
        assert response.status_code == 404
        assert not LeagueMembership.objects.filter(user=outsider, league=league).exists()


# ---------------------------------------------------------------------------
# Admin "members only" validation
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestAdminCoCommissionerValidation:
    def _base_data(self, league, co_ids):
        return {
            'name': league.name,
            'commissioner': league.commissioner_id,
            'sport': league.sport,
            'description': league.description or '',
            'co_commissioners': co_ids,
        }

    def test_member_can_be_co_commissioner(self, league, plain_member):
        form = LeagueAdminForm(
            data=self._base_data(league, [plain_member.id]), instance=league
        )
        assert form.is_valid(), form.errors

    def test_non_member_rejected(self, league, outsider):
        form = LeagueAdminForm(
            data=self._base_data(league, [outsider.id]), instance=league
        )
        assert not form.is_valid()
        assert 'co_commissioners' in form.errors


# ---------------------------------------------------------------------------
# My Leagues page shows the Manage shortcut for commissioners
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestMyLeaguesManageLink:
    def test_primary_commissioner_sees_manage_link(self, league):
        client = Client()
        client.force_login(league.commissioner)
        response = client.get(reverse('my_leagues'))
        assert response.status_code == 200
        assert reverse('manage_league', args=[league.id]).encode() in response.content

    def test_co_commissioner_sees_manage_link(self, league, co_commissioner):
        client = Client()
        client.force_login(co_commissioner)
        response = client.get(reverse('my_leagues'))
        assert response.status_code == 200
        assert reverse('manage_league', args=[league.id]).encode() in response.content

    def test_plain_member_does_not_see_manage_link(self, league, plain_member):
        client = Client()
        client.force_login(plain_member)
        response = client.get(reverse('my_leagues'))
        assert response.status_code == 200
        assert reverse('manage_league', args=[league.id]).encode() not in response.content


# ---------------------------------------------------------------------------
# Auth flow: `next` is honored (and open-redirects are blocked)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestNextRedirects:
    def test_login_honors_safe_next(self, user):
        client = Client()
        response = client.post(reverse('login') + '?next=/leagues/', {
            'username': 'testplayer',
            'password': 'testpass123',
            'next': '/leagues/',
        })
        assert response.status_code == 302
        assert response.url == '/leagues/'

    def test_login_ignores_unsafe_next(self, user):
        client = Client()
        response = client.post(reverse('login'), {
            'username': 'testplayer',
            'password': 'testpass123',
            'next': 'https://evil.example.com/',
        })
        assert response.status_code == 302
        assert 'evil.example.com' not in response.url

    def test_signup_honors_safe_next(self):
        client = Client()
        response = client.post(reverse('signup'), {
            'username': 'invitee',
            'email': 'invitee@test.com',
            'team_name': 'InviteeTeam',
            'password1': 'strongpass123!',
            'password2': 'strongpass123!',
            'next': '/leagues/',
        })
        assert response.status_code == 302
        assert response.url == '/leagues/'

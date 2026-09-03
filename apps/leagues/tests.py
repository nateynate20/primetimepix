from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.users.models import Profile
from apps.games.models import Game
from apps.games.utils import season_has_started
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
    def test_landing_page_shows_league(self, league, outsider):
        client = Client()
        client.force_login(outsider)
        response = client.get(reverse('join_via_invite', args=[league.join_code]))
        assert response.status_code == 200
        assert league.name.encode() in response.content
        # GET is a preview only — it must not join the user.
        assert not LeagueMembership.objects.filter(user=outsider, league=league).exists()

    def test_authenticated_user_joins_on_post(self, league, outsider):
        client = Client()
        client.force_login(outsider)
        response = client.post(reverse('join_via_invite', args=[league.join_code]))
        assert response.status_code == 302
        assert LeagueMembership.objects.filter(user=outsider, league=league).exists()

    def test_returning_from_signup_auto_joins(self, league, outsider):
        """After signup the user lands back here authenticated with ?join=1, and
        must be added to the league without having to click Join a second time."""
        client = Client()
        client.force_login(outsider)
        response = client.get(
            reverse('join_via_invite', args=[league.join_code]), {'join': '1'}
        )
        assert response.status_code == 302
        assert response.url == reverse('league_detail', args=[league.id])
        assert LeagueMembership.objects.filter(user=outsider, league=league).exists()

    def test_anonymous_post_carries_join_flag_into_signup(self, league):
        """The signup redirect must preserve the join intent so registration
        flows straight into membership."""
        client = Client()
        response = client.post(reverse('join_via_invite', args=[league.join_code]))
        assert response.status_code == 302
        assert reverse('signup') in response.url
        # next=...%3Fjoin%3D1  (URL-encoded "?join=1")
        assert 'join%3D1' in response.url

    def test_join_code_lookup_is_case_insensitive(self, league, outsider):
        client = Client()
        client.force_login(outsider)
        response = client.get(
            reverse('join_via_invite', args=[league.join_code.lower()])
        )
        assert response.status_code == 200

    def test_anonymous_sees_landing_page(self, league):
        client = Client()
        response = client.get(reverse('join_via_invite', args=[league.join_code]))
        assert response.status_code == 200
        assert reverse('signup').encode() in response.content

    def test_anonymous_post_routed_to_signup(self, league):
        client = Client()
        response = client.post(reverse('join_via_invite', args=[league.join_code]))
        assert response.status_code == 302
        assert reverse('signup') in response.url
        assert 'next=' in response.url

    def test_old_uuid_link_redirects_to_short_link(self, league, outsider):
        client = Client()
        client.force_login(outsider)
        response = client.get(reverse('invite_redirect', args=[league.invite_code]))
        assert response.status_code == 302
        assert league.join_code in response.url

    def test_regenerate_invalidates_old_link(self, league, outsider):
        old_code = league.join_code
        client = Client()
        client.force_login(league.commissioner)
        response = client.post(reverse('regenerate_invite', args=[league.id]))
        assert response.status_code == 302
        league.refresh_from_db()
        assert league.join_code != old_code

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


@pytest.mark.django_db
class TestJoinCodes:
    def test_join_code_autogenerated_and_unambiguous(self, league):
        assert league.join_code
        assert len(league.join_code) == 8
        # No ambiguous characters.
        assert not (set(league.join_code) & set('O0I1'))

    def test_join_codes_are_unique(self, league):
        other = League.objects.create(
            name='Second League', commissioner=league.commissioner,
            sport='NFL', is_approved=True,
        )
        assert other.join_code != league.join_code

    def test_commissioner_sets_custom_code(self, league):
        client = Client()
        client.force_login(league.commissioner)
        response = client.post(reverse('manage_league', args=[league.id]), {
            'name': league.name,
            'description': '',
            'join_code': 'chiefs24',
        })
        assert response.status_code == 302
        league.refresh_from_db()
        assert league.join_code == 'CHIEFS24'  # normalized to uppercase

    def test_duplicate_custom_code_rejected(self, league):
        taken = League.objects.create(
            name='Taken League', commissioner=league.commissioner,
            sport='NFL', is_approved=True, join_code='SHARED1',
        )
        client = Client()
        client.force_login(league.commissioner)
        response = client.post(reverse('manage_league', args=[league.id]), {
            'name': league.name,
            'description': '',
            'join_code': 'SHARED1',
        })
        assert response.status_code == 200  # re-renders with error
        league.refresh_from_db()
        assert league.join_code != 'SHARED1'

    def test_invalid_custom_code_rejected(self, league):
        client = Client()
        client.force_login(league.commissioner)
        response = client.post(reverse('manage_league', args=[league.id]), {
            'name': league.name,
            'description': '',
            'join_code': 'bad code!',  # spaces + punctuation not allowed
        })
        assert response.status_code == 200
        league.refresh_from_db()
        assert league.join_code != 'BAD CODE!'


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


# ---------------------------------------------------------------------------
# Joining closes once the season starts (no late entry after kickoff)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestSeasonStartLocksJoining:
    def _past_game(self):
        return Game.objects.create(
            game_id='lock_started_1', season=2026, week=1, game_type='regular',
            start_time=timezone.now() - timedelta(hours=1),
            home_team='Kansas City Chiefs', away_team='Buffalo Bills',
            status='in_progress',
        )

    def _future_game(self):
        return Game.objects.create(
            game_id='lock_future_1', season=2026, week=1, game_type='regular',
            start_time=timezone.now() + timedelta(days=3),
            home_team='Kansas City Chiefs', away_team='Buffalo Bills',
            status='scheduled',
        )

    def test_season_not_started_without_games(self, db):
        assert season_has_started() is False

    def test_season_not_started_with_only_future_games(self, db):
        self._future_game()
        assert season_has_started() is False

    def test_season_started_once_a_game_has_kicked_off(self, db):
        self._future_game()
        self._past_game()
        assert season_has_started() is True

    def test_invite_join_blocked_after_kickoff(self, league, outsider):
        self._past_game()
        client = Client()
        client.force_login(outsider)
        response = client.post(reverse('join_via_invite', args=[league.join_code]))
        assert response.status_code == 302
        assert not LeagueMembership.objects.filter(user=outsider, league=league).exists()

    def test_invite_join_allowed_before_kickoff(self, league, outsider):
        self._future_game()
        client = Client()
        client.force_login(outsider)
        response = client.post(reverse('join_via_invite', args=[league.join_code]))
        assert response.status_code == 302
        assert LeagueMembership.objects.filter(user=outsider, league=league).exists()

    def test_instant_join_blocked_after_kickoff(self, league, outsider):
        self._past_game()
        client = Client()
        client.force_login(outsider)
        response = client.post(reverse('join_league_instant', args=[league.id]))
        assert response.status_code == 302
        assert not LeagueMembership.objects.filter(user=outsider, league=league).exists()

    def test_existing_member_can_still_open_league_after_kickoff(self, league, plain_member):
        self._past_game()
        client = Client()
        client.force_login(plain_member)
        response = client.get(reverse('league_detail', args=[league.id]))
        assert response.status_code == 200

    def test_landing_page_shows_locked_state(self, league, outsider):
        self._past_game()
        client = Client()
        client.force_login(outsider)
        response = client.get(reverse('join_via_invite', args=[league.join_code]))
        assert response.status_code == 200
        assert b'Joining Closed' in response.content

    def test_share_includes_join_link_when_open(self, league):
        # Before kickoff the sharable standings still carry the join link.
        self._future_game()
        client = Client()
        client.force_login(league.commissioner)  # commissioner is a member
        response = client.get(reverse('league_detail', args=[league.id]))
        assert response.status_code == 200
        assert league.join_code.encode() in response.content

    def test_share_omits_join_link_when_locked(self, league):
        # Once locked, the dead join link is dropped from the share payload.
        self._past_game()
        client = Client()
        client.force_login(league.commissioner)
        response = client.get(reverse('league_detail', args=[league.id]))
        assert response.status_code == 200
        assert league.join_code.encode() not in response.content

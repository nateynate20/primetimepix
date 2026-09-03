"""End-to-end integration tests that simulate one full NFL week the way a
live season runs it:

    1. Users submit picks while games are open (through the real service).
    2. Games kick off and finish with scores.
    3. The results cron command (`calculate_results`) grades every pick.
    4. League standings reflect the correct outcomes.

These tests use real models and the real management command (no network, no
ESPN calls) and assert that re-running the pipeline is idempotent — the single
most important property for a cron job that may fire more than once.
"""
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.games.models import Game
from apps.leagues.models import League, LeagueMembership
from apps.picks.models import Pick, UserStats, LeagueStats
from apps.picks.services import PickService


def _make_open_game(game_id, home, away, week=1):
    """A future, still-pickable game."""
    return Game.objects.create(
        game_id=game_id, season=2026, week=week, game_type='regular',
        start_time=timezone.now() + timedelta(days=1),
        home_team=home, away_team=away, status='scheduled',
    )


def _finish_game(game, home_score, away_score):
    """Simulate kickoff passing and the final score arriving."""
    game.start_time = timezone.now() - timedelta(hours=3)
    game.home_score = home_score
    game.away_score = away_score
    game.status = 'final'
    game.save()


@pytest.fixture
def week_scenario(db, user, second_user):
    """A league with two members who have picked a 3-game primetime slate."""
    league = League.objects.create(
        name='Pipeline League', commissioner=user, sport='NFL', is_approved=True,
    )
    LeagueMembership.objects.get_or_create(user=user, league=league)
    LeagueMembership.objects.get_or_create(user=second_user, league=league)

    tnf = _make_open_game('pipe_tnf', 'Kansas City Chiefs', 'Buffalo Bills')
    snf = _make_open_game('pipe_snf', 'Philadelphia Eagles', 'Dallas Cowboys')
    mnf = _make_open_game('pipe_mnf', 'New York Giants', 'Washington Commanders')

    # user picks all favorites; second_user picks all underdogs.
    saved_a, err_a = PickService.save_user_picks(user, {
        tnf.id: {'team': 'Kansas City Chiefs', 'confidence': 1},
        snf.id: {'team': 'Philadelphia Eagles', 'confidence': 1},
        mnf.id: {'team': 'New York Giants', 'confidence': 1},
    }, league=league)
    saved_b, err_b = PickService.save_user_picks(second_user, {
        tnf.id: {'team': 'Buffalo Bills', 'confidence': 1},
        snf.id: {'team': 'Dallas Cowboys', 'confidence': 1},
        mnf.id: {'team': 'Washington Commanders', 'confidence': 1},
    }, league=league)

    # Sanity: picks were accepted while games were open.
    assert len(saved_a) == 3 and err_a == []
    assert len(saved_b) == 3 and err_b == []

    # Games finish: KC wins, Eagles win, MNF is a tie (push for everyone).
    _finish_game(tnf, home_score=27, away_score=24)
    _finish_game(snf, home_score=20, away_score=10)
    _finish_game(mnf, home_score=21, away_score=21)

    return {'league': league, 'user': user, 'second_user': second_user,
            'tnf': tnf, 'snf': snf, 'mnf': mnf}


def _run_results():
    out = StringIO()
    call_command('calculate_results', '--all', stdout=out)
    return out.getvalue()


def _row(standings, target_user):
    """Pull one member's standings row regardless of current rank order."""
    return next(r for r in standings if r['user'] == target_user)


@pytest.mark.django_db
class TestSeasonWeekPipeline:
    def test_full_week_grades_picks_and_standings(self, week_scenario):
        league = week_scenario['league']
        user = week_scenario['user']
        second_user = week_scenario['second_user']

        _run_results()

        # user: KC correct, Eagles correct, MNF push (None). 2 resolved, 2 pts.
        assert Pick.objects.get(user=user, game=week_scenario['tnf']).is_correct is True
        assert Pick.objects.get(user=user, game=week_scenario['snf']).is_correct is True
        assert Pick.objects.get(user=user, game=week_scenario['mnf']).is_correct is None

        # second_user: BUF wrong, Cowboys wrong, MNF push. 2 resolved, 0 pts.
        assert Pick.objects.get(user=second_user, game=week_scenario['tnf']).is_correct is False
        assert Pick.objects.get(user=second_user, game=week_scenario['snf']).is_correct is False

        standings = league.get_standings()
        # Winner is the favorites-picker with 2 points.
        assert standings[0]['user'] == user
        assert standings[0]['total_points'] == 2
        assert standings[0]['correct_predictions'] == 2
        assert standings[1]['user'] == second_user
        assert standings[1]['total_points'] == 0


@pytest.mark.django_db
class TestResultsIdempotency:
    """Running the grading cron twice must not change any result — this is what
    protects us if the scheduler double-fires or we re-run a week manually."""

    def test_double_run_leaves_standings_identical(self, week_scenario):
        league = week_scenario['league']

        _run_results()
        first = league.get_standings()

        _run_results()
        second = league.get_standings()

        assert first == second

    def test_double_run_does_not_change_pick_points(self, week_scenario):
        _run_results()
        snapshot = {
            p.id: (p.is_correct, p.points)
            for p in Pick.objects.all()
        }
        _run_results()
        after = {
            p.id: (p.is_correct, p.points)
            for p in Pick.objects.all()
        }
        assert snapshot == after

    def test_user_and_league_stats_recompute_is_idempotent(self, week_scenario):
        user = week_scenario['user']
        league = week_scenario['league']
        _run_results()

        stats = UserStats.get_or_create_for_user(user)
        stats.update_stats()
        stats.refresh_from_db()
        first = (stats.total_picks, stats.correct_picks, stats.win_percentage)

        stats.update_stats()
        stats.refresh_from_db()
        second = (stats.total_picks, stats.correct_picks, stats.win_percentage)
        assert first == second

        lstats = LeagueStats.get_or_create_for_user_league(user, league)
        lstats.update_league_stats()
        lstats.refresh_from_db()
        first_l = (lstats.total_picks, lstats.correct_picks, lstats.total_points)
        lstats.update_league_stats()
        lstats.refresh_from_db()
        second_l = (lstats.total_picks, lstats.correct_picks, lstats.total_points)
        assert first_l == second_l


@pytest.fixture
def midweek_scenario(db, user, second_user):
    """Two members with picks on a 3-game primetime slate and NOTHING finished
    yet. The test drives games to 'final' one at a time so it can assert the
    standings update incrementally as each game concludes."""
    league = League.objects.create(
        name='Midweek League', commissioner=user, sport='NFL', is_approved=True,
    )
    LeagueMembership.objects.get_or_create(user=user, league=league)
    LeagueMembership.objects.get_or_create(user=second_user, league=league)

    tnf = _make_open_game('mid_tnf', 'Kansas City Chiefs', 'Buffalo Bills')
    snf = _make_open_game('mid_snf', 'Philadelphia Eagles', 'Dallas Cowboys')
    mnf = _make_open_game('mid_mnf', 'New York Giants', 'Washington Commanders')

    # user picks all favorites; second_user picks all underdogs.
    PickService.save_user_picks(user, {
        tnf.id: {'team': 'Kansas City Chiefs', 'confidence': 1},
        snf.id: {'team': 'Philadelphia Eagles', 'confidence': 1},
        mnf.id: {'team': 'New York Giants', 'confidence': 1},
    }, league=league)
    PickService.save_user_picks(second_user, {
        tnf.id: {'team': 'Buffalo Bills', 'confidence': 1},
        snf.id: {'team': 'Dallas Cowboys', 'confidence': 1},
        mnf.id: {'team': 'Washington Commanders', 'confidence': 1},
    }, league=league)

    return {'league': league, 'user': user, 'second_user': second_user,
            'tnf': tnf, 'snf': snf, 'mnf': mnf}


@pytest.mark.django_db
class TestMidweekPartialStandings:
    """Standings must reflect only games that have concluded, updating game by
    game: a correct pick becomes a win, a wrong pick a loss, and picks for games
    still to be played stay 'pending' (never counted as a win or a loss)."""

    def test_before_any_game_finishes_everything_is_pending(self, midweek_scenario):
        league = midweek_scenario['league']
        user = midweek_scenario['user']

        _run_results()  # no games are final yet -> nothing gets graded

        row = _row(league.get_standings(), user)
        assert (row['wins'], row['losses'], row['pending']) == (0, 0, 3)
        assert row['record'] == '0-0'
        assert row['total_points'] == 0
        assert row['total_predictions'] == 0  # no decided games

    def test_after_thursday_only_that_game_counts(self, midweek_scenario):
        league = midweek_scenario['league']
        user = midweek_scenario['user']
        second_user = midweek_scenario['second_user']

        # Thursday night concludes: Kansas City beats Buffalo.
        _finish_game(midweek_scenario['tnf'], home_score=27, away_score=24)
        _run_results()

        standings = league.get_standings()
        u = _row(standings, user)          # picked KC -> win
        s = _row(standings, second_user)   # picked BUF -> loss

        assert (u['wins'], u['losses'], u['pending']) == (1, 0, 2)
        assert u['record'] == '1-0'
        assert u['total_points'] == 1
        assert u['accuracy'] == 100.0

        assert (s['wins'], s['losses'], s['pending']) == (0, 1, 2)
        assert s['record'] == '0-1'
        assert s['total_points'] == 0
        assert s['accuracy'] == 0

        # Favorites-picker leads on points after one game.
        assert standings[0]['user'] == user

    def test_sunday_night_updates_record_incrementally(self, midweek_scenario):
        league = midweek_scenario['league']
        user = midweek_scenario['user']
        second_user = midweek_scenario['second_user']

        # Thursday finishes and is graded...
        _finish_game(midweek_scenario['tnf'], home_score=27, away_score=24)
        _run_results()
        # ...then Sunday night finishes too (Eagles win). Monday still to play.
        _finish_game(midweek_scenario['snf'], home_score=20, away_score=10)
        _run_results()

        standings = league.get_standings()
        u = _row(standings, user)
        s = _row(standings, second_user)

        # A second correct pick flips one pending game into a win.
        assert (u['wins'], u['losses'], u['pending']) == (2, 0, 1)
        assert u['record'] == '2-0'
        assert u['total_points'] == 2

        assert (s['wins'], s['losses'], s['pending']) == (0, 2, 1)
        assert s['record'] == '0-2'
        assert s['total_points'] == 0

    def test_tie_game_is_a_push_not_a_loss(self, midweek_scenario):
        league = midweek_scenario['league']
        user = midweek_scenario['user']

        # Monday night ends in a tie -> push: not a win, not a loss, no points.
        _finish_game(midweek_scenario['mnf'], home_score=21, away_score=21)
        _run_results()

        row = _row(league.get_standings(), user)
        assert (row['wins'], row['losses']) == (0, 0)
        assert row['pushes'] == 1
        assert row['pending'] == 2          # TNF + SNF still to play
        assert row['record'] == '0-0-1'     # push shown as the third figure
        assert row['total_points'] == 0

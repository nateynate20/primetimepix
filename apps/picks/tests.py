import pytest
from apps.picks.models import Pick, CPUPick, UserStats
from apps.picks.services import PickService
from apps.games.models import Game
from django.utils import timezone
from datetime import timedelta


@pytest.mark.django_db
class TestPickCalculateResult:
    def test_correct_pick_home_wins(self, user, finished_game):
        pick = Pick.objects.create(
            user=user, game=finished_game, picked_team='Kansas City Chiefs'
        )
        result = pick.calculate_result()
        assert result is True
        pick.refresh_from_db()
        assert pick.is_correct is True
        assert pick.points == 1

    def test_incorrect_pick(self, user, finished_game):
        pick = Pick.objects.create(
            user=user, game=finished_game, picked_team='Buffalo Bills'
        )
        result = pick.calculate_result()
        assert result is False
        pick.refresh_from_db()
        assert pick.is_correct is False
        assert pick.points == 0

    def test_pick_with_confidence(self, user, finished_game):
        pick = Pick.objects.create(
            user=user, game=finished_game,
            picked_team='Kansas City Chiefs', confidence=3,
        )
        pick.calculate_result()
        pick.refresh_from_db()
        assert pick.is_correct is True
        assert pick.points == 3

    def test_incorrect_pick_zero_points_regardless_of_confidence(self, user, finished_game):
        pick = Pick.objects.create(
            user=user, game=finished_game,
            picked_team='Buffalo Bills', confidence=5,
        )
        pick.calculate_result()
        pick.refresh_from_db()
        assert pick.is_correct is False
        assert pick.points == 0

    def test_tie_game_pick_is_push(self, user, db):
        game = Game.objects.create(
            game_id='tie_1', season=2026, week=1, game_type='regular',
            start_time=timezone.now() - timedelta(days=1),
            home_team='Kansas City Chiefs', away_team='Buffalo Bills',
            home_score=24, away_score=24, status='final',
        )
        pick = Pick.objects.create(user=user, game=game, picked_team='Kansas City Chiefs')
        pick.calculate_result()
        pick.refresh_from_db()
        assert pick.is_correct is None
        assert pick.points == 0

    def test_pick_on_unfinished_game_returns_none(self, user, future_game):
        pick = Pick.objects.create(
            user=user, game=future_game, picked_team='Kansas City Chiefs'
        )
        result = pick.calculate_result()
        assert result is None

    def test_result_status_property(self, user, finished_game, future_game):
        correct_pick = Pick.objects.create(
            user=user, game=finished_game, picked_team='Kansas City Chiefs'
        )
        correct_pick.calculate_result()
        assert correct_pick.result_status == 'Correct'

        pending_pick = Pick.objects.create(
            user=user, game=future_game, picked_team='Buffalo Bills'
        )
        assert pending_pick.result_status == 'Pending'


@pytest.mark.django_db
class TestCPUPick:
    def test_cpu_correct_pick(self, finished_game):
        cpu = CPUPick.objects.create(
            game=finished_game, picked_team='Kansas City Chiefs'
        )
        result = cpu.resolve()
        assert result is True
        cpu.refresh_from_db()
        assert cpu.is_correct is True

    def test_cpu_incorrect_pick(self, finished_game):
        cpu = CPUPick.objects.create(
            game=finished_game, picked_team='Buffalo Bills'
        )
        result = cpu.resolve()
        assert result is False
        cpu.refresh_from_db()
        assert cpu.is_correct is False

    def test_cpu_pick_unfinished_game(self, future_game):
        cpu = CPUPick.objects.create(
            game=future_game, picked_team='Kansas City Chiefs'
        )
        result = cpu.resolve()
        assert result is None
        cpu.refresh_from_db()
        assert cpu.is_correct is None

    def test_cpu_pick_tie_game(self, db):
        game = Game.objects.create(
            game_id='cpu_tie', season=2026, week=1, game_type='regular',
            start_time=timezone.now() - timedelta(days=1),
            home_team='Kansas City Chiefs', away_team='Buffalo Bills',
            home_score=24, away_score=24, status='final',
        )
        cpu = CPUPick.objects.create(game=game, picked_team='Kansas City Chiefs')
        cpu.resolve()
        cpu.refresh_from_db()
        assert cpu.is_correct is None


@pytest.mark.django_db
class TestGameUpdatePickResults:
    def test_updates_picks_when_game_finishes(self, user, second_user):
        game = Game.objects.create(
            game_id='update_results_1', season=2026, week=1, game_type='regular',
            start_time=timezone.now() - timedelta(days=1),
            home_team='Kansas City Chiefs', away_team='Buffalo Bills',
            home_score=31, away_score=17, status='final',
        )
        Pick.objects.create(user=user, game=game, picked_team='Kansas City Chiefs')
        Pick.objects.create(user=second_user, game=game, picked_team='Buffalo Bills')

        game.update_pick_results()

        pick1 = Pick.objects.get(user=user, game=game)
        pick2 = Pick.objects.get(user=second_user, game=game)
        assert pick1.is_correct is True
        assert pick2.is_correct is False

    def test_does_not_update_if_game_not_final(self, user, future_game):
        Pick.objects.create(user=user, game=future_game, picked_team='Kansas City Chiefs')
        result = future_game.update_pick_results()
        assert result == 0

    def test_resolves_cpu_pick_too(self, finished_game):
        CPUPick.objects.create(game=finished_game, picked_team='Kansas City Chiefs')
        finished_game.update_pick_results()
        cpu = CPUPick.objects.get(game=finished_game)
        assert cpu.is_correct is True


@pytest.mark.django_db
class TestUserStats:
    def test_stats_created_for_user(self, user):
        stats = UserStats.get_or_create_for_user(user)
        assert stats.total_picks == 0
        assert stats.win_percentage == 0.0

    def test_stats_update_after_picks(self, user, finished_game):
        Pick.objects.create(
            user=user, game=finished_game, picked_team='Kansas City Chiefs'
        )
        pick = Pick.objects.get(user=user, game=finished_game)
        pick.calculate_result()

        stats = UserStats.get_or_create_for_user(user)
        stats.update_stats()
        stats.refresh_from_db()
        assert stats.total_picks == 1
        assert stats.correct_picks == 1
        assert stats.win_percentage == 100.0

    def test_total_points_excludes_unresolved_picks(self, user, finished_game, future_game):
        """total_points must count only resolved, correct picks — an open
        pick keeps the default points=1 and must not inflate the total."""
        # Correct resolved pick (confidence 3 -> 3 points).
        correct = Pick.objects.create(
            user=user, game=finished_game,
            picked_team='Kansas City Chiefs', confidence=3,
        )
        correct.calculate_result()
        # Open pick for a future game: unresolved, still has default points=1.
        Pick.objects.create(user=user, game=future_game, picked_team='Kansas City Chiefs')

        stats = UserStats.get_or_create_for_user(user)
        stats.update_stats()
        stats.refresh_from_db()

        assert stats.total_picks == 1  # only the resolved pick counts
        assert stats.correct_picks == 1
        assert stats.total_points == 3  # NOT 4 (the unresolved pick is excluded)

    def test_total_points_excludes_incorrect_picks(self, user, finished_game):
        """Incorrect picks score 0 and must not add to total_points."""
        wrong = Pick.objects.create(
            user=user, game=finished_game,
            picked_team='Buffalo Bills', confidence=5,
        )
        wrong.calculate_result()
        stats = UserStats.get_or_create_for_user(user)
        stats.update_stats()
        stats.refresh_from_db()
        assert stats.total_points == 0


@pytest.mark.django_db
class TestLeagueStatsPoints:
    def test_league_total_points_excludes_unresolved(self, user, league, finished_game, future_game):
        from apps.picks.models import LeagueStats
        correct = Pick.objects.create(
            user=user, game=finished_game, league=league,
            picked_team='Kansas City Chiefs', confidence=2,
        )
        correct.calculate_result()
        # Open pick in the same league: unresolved, default points=1.
        Pick.objects.create(
            user=user, game=future_game, league=league, picked_team='Kansas City Chiefs'
        )

        lstats = LeagueStats.get_or_create_for_user_league(user, league)
        lstats.update_league_stats()
        lstats.refresh_from_db()

        assert lstats.total_picks == 1
        assert lstats.correct_picks == 1
        assert lstats.total_points == 2  # NOT 3


@pytest.mark.django_db
class TestGameLockSemantics:
    """The kickoff lock is the single most important correctness rule."""

    def test_future_scheduled_game_is_pickable(self, future_game):
        assert future_game.has_started is False
        assert future_game.is_locked is False
        assert future_game.can_make_picks() is True

    def test_started_game_is_locked(self):
        game = Game.objects.create(
            game_id='started_1', season=2026, week=1, game_type='regular',
            start_time=timezone.now() - timedelta(minutes=1),
            home_team='Kansas City Chiefs', away_team='Buffalo Bills',
            status='scheduled',
        )
        assert game.has_started is True
        assert game.can_make_picks() is False

    def test_final_game_is_locked(self, finished_game):
        assert finished_game.can_make_picks() is False


@pytest.mark.django_db
class TestPickLockingServerSide:
    """Server-side enforcement: picks must be rejected after kickoff even if
    a crafted/replayed request bypasses the UI. Guards against a future
    refactor silently turning this into a UI-only check."""

    def test_service_saves_pick_before_kickoff(self, user, future_game):
        picks_data = {future_game.id: {'team': 'Kansas City Chiefs', 'confidence': 1}}
        saved, errors = PickService.save_user_picks(user, picks_data)
        assert len(saved) == 1
        assert errors == []
        assert Pick.objects.filter(user=user, game=future_game).exists()

    def test_service_rejects_pick_after_kickoff(self, user):
        started = Game.objects.create(
            game_id='locked_post', season=2026, week=1, game_type='regular',
            start_time=timezone.now() - timedelta(minutes=1),
            home_team='Kansas City Chiefs', away_team='Buffalo Bills',
            status='scheduled',
        )
        picks_data = {started.id: {'team': 'Kansas City Chiefs', 'confidence': 1}}
        saved, errors = PickService.save_user_picks(user, picks_data)
        assert saved == []
        assert len(errors) == 1
        assert 'closed' in errors[0].lower()
        # Critically: nothing was written to the database.
        assert not Pick.objects.filter(user=user, game=started).exists()

    def test_service_cannot_change_existing_pick_after_kickoff(self, user, future_game):
        # Make a legit pick while the game is open.
        PickService.save_user_picks(
            user, {future_game.id: {'team': 'Kansas City Chiefs', 'confidence': 1}}
        )
        # Simulate kickoff passing.
        future_game.start_time = timezone.now() - timedelta(minutes=1)
        future_game.save(update_fields=['start_time'])
        # Attempt to flip the pick after kickoff.
        saved, errors = PickService.save_user_picks(
            user, {future_game.id: {'team': 'Buffalo Bills', 'confidence': 1}}
        )
        assert saved == []
        assert len(errors) == 1
        Pick.objects.get(user=user, game=future_game).refresh_from_db()
        assert Pick.objects.get(user=user, game=future_game).picked_team == 'Kansas City Chiefs'

    def test_view_rejects_pick_after_kickoff(self, client, user):
        """End-to-end through the schedule POST view. Uses a fixed past
        Thursday-night slot so the game is deterministically primetime AND
        already kicked off, regardless of when the test runs."""
        import pytz
        from datetime import datetime
        from apps.leagues.models import League, LeagueMembership
        league = League.objects.create(
            name='Lock Test League', commissioner=user, sport='NFL', is_approved=True,
        )
        LeagueMembership.objects.get_or_create(user=user, league=league)
        # 2024-09-05 20:15 ET (Thursday night, week 1 opener) -> primetime + past.
        kickoff = pytz.UTC.localize(datetime(2024, 9, 6, 0, 15))
        started = Game.objects.create(
            game_id='view_locked', season=2024, week=1, game_type='regular',
            start_time=kickoff,
            home_team='Kansas City Chiefs', away_team='Buffalo Bills',
            status='scheduled',
        )
        assert started.is_primetime is True
        assert started.has_started is True
        client.force_login(user)
        client.post(
            f"/picks/?week=1&league={league.id}",
            {'pick_' + str(started.id): 'home', 'league': str(league.id)},
        )
        assert not Pick.objects.filter(user=user, game=started).exists()


class TestBadges:
    """compute_badges is pure (no DB) — it derives achievements from stats."""

    def _stats(self, **kw):
        from types import SimpleNamespace
        base = dict(total_picks=0, best_streak=0, win_percentage=0.0, primetime_correct=0)
        base.update(kw)
        return SimpleNamespace(**base)

    def test_new_user_earns_nothing(self):
        from apps.picks.badges import compute_badges
        badges = compute_badges(self._stats())
        assert all(not b['earned'] for b in badges)

    def test_first_pick_earns_on_board(self):
        from apps.picks.badges import compute_badges
        earned = {b['key'] for b in compute_badges(self._stats(total_picks=1)) if b['earned']}
        assert earned == {'on_board'}

    def test_thresholds_unlock_expected_badges(self):
        from apps.picks.badges import compute_badges
        stats = self._stats(total_picks=10, best_streak=5, win_percentage=70.0, primetime_correct=10)
        earned = {b['key'] for b in compute_badges(stats) if b['earned']}
        assert {'on_board', 'regular', 'hot_hand', 'unstoppable', 'sharpshooter', 'primetime_pro'} <= earned
        # Perfectionist needs a 10-game win streak.
        assert 'perfectionist' not in earned

    def test_sharpshooter_requires_minimum_picks(self):
        from apps.picks.badges import compute_badges
        # 100% accuracy but only 3 picks — not enough sample to earn it.
        earned = {b['key'] for b in compute_badges(self._stats(total_picks=3, win_percentage=100.0)) if b['earned']}
        assert 'sharpshooter' not in earned

    def test_locked_badges_expose_progress(self):
        from apps.picks.badges import compute_badges
        regular = next(b for b in compute_badges(self._stats(total_picks=4)) if b['key'] == 'regular')
        assert regular['earned'] is False
        assert regular['progress'] == '4/10'

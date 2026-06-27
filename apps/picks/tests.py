import pytest
from apps.picks.models import Pick, CPUPick, UserStats
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

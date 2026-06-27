import pytest
from apps.games.models import Game
from django.utils import timezone
from datetime import timedelta, datetime
import pytz


@pytest.mark.django_db
class TestGameWinner:
    def test_home_team_wins(self, finished_game):
        assert finished_game.winner == 'Kansas City Chiefs'

    def test_away_team_wins(self, db):
        game = Game.objects.create(
            game_id='away_wins', season=2026, week=1, game_type='regular',
            start_time=timezone.now() - timedelta(days=1),
            home_team='Kansas City Chiefs', away_team='Buffalo Bills',
            home_score=20, away_score=31, status='final',
        )
        assert game.winner == 'Buffalo Bills'

    def test_tie_game(self, db):
        game = Game.objects.create(
            game_id='tie_game', season=2026, week=1, game_type='regular',
            start_time=timezone.now() - timedelta(days=1),
            home_team='Kansas City Chiefs', away_team='Buffalo Bills',
            home_score=24, away_score=24, status='final',
        )
        assert game.winner == 'tie'

    def test_no_winner_when_not_final(self, future_game):
        assert future_game.winner is None

    def test_no_winner_when_scores_missing(self, db):
        game = Game.objects.create(
            game_id='no_scores', season=2026, week=1, game_type='regular',
            start_time=timezone.now() - timedelta(days=1),
            home_team='Kansas City Chiefs', away_team='Buffalo Bills',
            status='final',
        )
        assert game.winner is None


@pytest.mark.django_db
class TestGamePickability:
    def test_can_pick_future_game(self, future_game):
        assert future_game.can_make_picks() is True

    def test_cannot_pick_started_game(self, finished_game):
        assert finished_game.can_make_picks() is False

    def test_cannot_pick_in_progress_game(self, db):
        game = Game.objects.create(
            game_id='in_progress_1', season=2026, week=1, game_type='regular',
            start_time=timezone.now() - timedelta(hours=1),
            home_team='Kansas City Chiefs', away_team='Buffalo Bills',
            status='in_progress',
        )
        assert game.can_make_picks() is False

    def test_is_locked_matches_can_make_picks(self, future_game, finished_game):
        assert future_game.is_locked is False
        assert finished_game.is_locked is True


@pytest.mark.django_db
class TestGamePrimetime:
    def test_thursday_night_is_primetime(self, thursday_night_game):
        assert thursday_night_game.is_primetime is True

    def test_sunday_afternoon_not_primetime(self, sunday_afternoon_game):
        assert sunday_afternoon_game.is_primetime is False

    def test_playoff_game_is_primetime(self, db):
        game = Game.objects.create(
            game_id='playoff_1', season=2026, week=19, game_type='playoff',
            start_time=timezone.now() + timedelta(days=30),
            home_team='Kansas City Chiefs', away_team='Buffalo Bills',
            status='scheduled',
        )
        assert game.is_primetime is True

    def test_superbowl_is_primetime(self, db):
        game = Game.objects.create(
            game_id='sb_1', season=2026, week=21, game_type='superbowl',
            start_time=timezone.now() + timedelta(days=60),
            home_team='Kansas City Chiefs', away_team='Philadelphia Eagles',
            status='scheduled',
        )
        assert game.is_primetime is True

    def test_monday_night_is_primetime(self, db):
        eastern = pytz.timezone('US/Eastern')
        next_monday = timezone.now() + timedelta(days=(0 - timezone.now().weekday()) % 7 + 7)
        game_time = eastern.localize(
            datetime(next_monday.year, next_monday.month, next_monday.day, 20, 15)
        )
        game = Game.objects.create(
            game_id='mnf_1', season=2026, week=3, game_type='regular',
            start_time=game_time,
            home_team='San Francisco 49ers', away_team='Dallas Cowboys',
            status='scheduled',
        )
        assert game.is_primetime is True
        assert game.primetime_type == 'Monday Night'

    def test_sunday_night_is_primetime(self, db):
        eastern = pytz.timezone('US/Eastern')
        next_sunday = timezone.now() + timedelta(days=(6 - timezone.now().weekday()) % 7 + 7)
        game_time = eastern.localize(
            datetime(next_sunday.year, next_sunday.month, next_sunday.day, 20, 20)
        )
        game = Game.objects.create(
            game_id='snf_1', season=2026, week=3, game_type='regular',
            start_time=game_time,
            home_team='Green Bay Packers', away_team='Chicago Bears',
            status='scheduled',
        )
        assert game.is_primetime is True
        assert game.primetime_type == 'Sunday Night'


@pytest.mark.django_db
class TestGameLogos:
    def test_home_logo_found(self, finished_game):
        assert finished_game.home_logo == 'https://a.espncdn.com/i/teamlogos/nfl/500/kc.png'

    def test_away_logo_found(self, finished_game):
        assert finished_game.away_logo == 'https://a.espncdn.com/i/teamlogos/nfl/500/buf.png'

    def test_logo_none_for_unknown_team(self, db):
        game = Game.objects.create(
            game_id='unknown_team', season=2026, week=1, game_type='regular',
            start_time=timezone.now() + timedelta(days=1),
            home_team='London Silly Nannies', away_team='Mars Aliens',
            status='scheduled',
        )
        assert game.home_logo is None
        assert game.away_logo is None


@pytest.mark.django_db
class TestGameStatus:
    def test_is_finished_final(self, finished_game):
        assert finished_game.is_finished is True

    def test_is_finished_scheduled(self, future_game):
        assert future_game.is_finished is False

    def test_display_status(self, finished_game, future_game):
        assert finished_game.display_status == 'Final'
        assert future_game.display_status == 'Scheduled'

    def test_str_representation(self, finished_game):
        assert str(finished_game) == 'Buffalo Bills @ Kansas City Chiefs (Week 1)'

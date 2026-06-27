import pytest
from django.contrib.auth import get_user_model
from apps.users.models import Profile
from apps.leagues.models import League, LeagueMembership
from apps.games.models import Game
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


@pytest.fixture
def user(db):
    u = User.objects.create_user(username='testplayer', password='testpass123', email='test@test.com')
    Profile.objects.filter(user=u).update(team_name='TestTeam')
    return u


@pytest.fixture
def second_user(db):
    u = User.objects.create_user(username='player2', password='testpass123', email='player2@test.com')
    Profile.objects.get_or_create(user=u, defaults={'team_name': 'Team2'})
    return u


@pytest.fixture
def league(db, user):
    league = League.objects.create(
        name='Test League',
        commissioner=user,
        sport='NFL',
        is_private=False,
        is_approved=True,
    )
    return league


@pytest.fixture
def future_game(db):
    return Game.objects.create(
        game_id='test_future_1',
        season=2026,
        week=1,
        game_type='regular',
        start_time=timezone.now() + timedelta(days=1),
        home_team='Kansas City Chiefs',
        away_team='Buffalo Bills',
        status='scheduled',
    )


@pytest.fixture
def finished_game(db):
    return Game.objects.create(
        game_id='test_finished_1',
        season=2026,
        week=1,
        game_type='regular',
        start_time=timezone.now() - timedelta(days=1),
        home_team='Kansas City Chiefs',
        away_team='Buffalo Bills',
        home_score=27,
        away_score=24,
        status='final',
    )


@pytest.fixture
def thursday_night_game(db):
    """A Thursday night primetime game."""
    from datetime import datetime
    import pytz

    eastern = pytz.timezone('US/Eastern')
    next_thursday = timezone.now() + timedelta(days=(3 - timezone.now().weekday()) % 7 + 7)
    game_time = eastern.localize(
        datetime(next_thursday.year, next_thursday.month, next_thursday.day, 20, 15)
    )
    return Game.objects.create(
        game_id='test_tnf_1',
        season=2026,
        week=2,
        game_type='regular',
        start_time=game_time,
        home_team='Philadelphia Eagles',
        away_team='Dallas Cowboys',
        status='scheduled',
    )


@pytest.fixture
def sunday_afternoon_game(db):
    """A Sunday 1pm game (NOT primetime)."""
    from datetime import datetime
    import pytz

    eastern = pytz.timezone('US/Eastern')
    next_sunday = timezone.now() + timedelta(days=(6 - timezone.now().weekday()) % 7 + 7)
    game_time = eastern.localize(
        datetime(next_sunday.year, next_sunday.month, next_sunday.day, 13, 0)
    )
    return Game.objects.create(
        game_id='test_sun_early_1',
        season=2026,
        week=2,
        game_type='regular',
        start_time=game_time,
        home_team='New York Giants',
        away_team='Washington Commanders',
        status='scheduled',
    )

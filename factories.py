"""factory_boy factories for PrimeTimePix.

Shared by the test suite and the ``seed_season`` management command so that
realistic, season-sized data can be generated on demand. Kept at the repo root
(next to ``conftest.py``) so both tests and management commands can import it
without coupling runtime code to the ``tests/`` tree.
"""
from datetime import timedelta

import factory
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.games.models import Game
from apps.leagues.models import League
from apps.picks.models import Pick

User = get_user_model()

# NFL team names that match the logo lookup in Game.TEAM_LOGOS.
NFL_TEAMS = [
    'Kansas City Chiefs', 'Buffalo Bills', 'Philadelphia Eagles', 'Dallas Cowboys',
    'San Francisco 49ers', 'Baltimore Ravens', 'Detroit Lions', 'Miami Dolphins',
    'Green Bay Packers', 'Cincinnati Bengals', 'New York Giants', 'Washington Commanders',
    'Pittsburgh Steelers', 'Seattle Seahawks', 'Los Angeles Rams', 'Minnesota Vikings',
]


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('username',)
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f'demo_user_{n}')
    email = factory.LazyAttribute(lambda o: f'{o.username}@example.com')

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            return
        self.set_password(extracted or 'demopass123')
        self.save()

    @factory.post_generation
    def team_name(self, create, extracted, **kwargs):
        if not create:
            return
        # Profile is auto-created by a post_save signal.
        if extracted and hasattr(self, 'profile'):
            self.profile.team_name = extracted
            self.profile.save(update_fields=['team_name'])


class LeagueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = League
        django_get_or_create = ('name',)

    name = factory.Sequence(lambda n: f'Demo League {n}')
    commissioner = factory.SubFactory(UserFactory)
    sport = 'NFL'
    is_approved = True
    is_private = False


class GameFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Game
        django_get_or_create = ('game_id',)

    game_id = factory.Sequence(lambda n: f'demo_game_{n}')
    season = 2026
    week = 1
    game_type = 'regular'
    start_time = factory.LazyFunction(lambda: timezone.now() + timedelta(days=1))
    home_team = factory.Iterator(NFL_TEAMS)
    away_team = factory.Iterator(list(reversed(NFL_TEAMS)))
    status = 'scheduled'


class PickFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Pick

    user = factory.SubFactory(UserFactory)
    game = factory.SubFactory(GameFactory)
    league = None
    picked_team = factory.LazyAttribute(lambda o: o.game.home_team)
    confidence = 1

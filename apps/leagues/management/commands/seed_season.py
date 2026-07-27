"""Seed a scoped, realistic slice of an NFL season for local/staging testing.

Generates recognizable personas, leagues of varying sizes, and one primetime
week (Thursday / Sunday / Monday night) with weighted pick distributions and
imperfect participation — so the app behaves the way it will in September
instead of with two tidy test users.

Everything it creates is namespaced (``demo_*`` usernames, ``Demo League``
names, ``demo_game_*`` ids) so ``--fresh`` can wipe it without touching real
data. Re-running without ``--fresh`` is idempotent.

Examples::

    python manage.py seed_season
    python manage.py seed_season --users 40 --fresh
    python manage.py seed_season --seed 7   # reproducible dataset
"""
import random
from datetime import datetime, timedelta

import pytz
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.games.models import Game
from apps.leagues.models import League, LeagueMembership
from apps.picks.models import Pick

from factories import UserFactory

EASTERN = pytz.timezone('US/Eastern')

# Recognizable testers make leaderboards believable during beta.
PERSONAS = [
    'Nathan', 'Mike', 'Ashley', 'Chris', 'Jordan', 'Taylor', 'Alex', 'Morgan',
    'Sam', 'Jamie', 'Casey', 'Riley', 'Drew', 'Quinn', 'Avery', 'Cameron',
    'Blake', 'Reese', 'Skyler', 'Devon', 'Harper', 'Rowan', 'Emerson', 'Parker',
]

LEAGUE_NAMES = [
    'Friends League', 'Work League', 'Family League', 'Fantasy Addicts',
    'The Underdogs', 'Primetime Pros',
]
LEAGUE_SIZES = [3, 6, 12, 18]


def _et(base_date, hour, minute):
    """Aware ET datetime on the given date."""
    return EASTERN.localize(datetime(base_date.year, base_date.month, base_date.day, hour, minute))


class Command(BaseCommand):
    help = 'Seed a scoped, realistic NFL primetime week for testing.'

    def add_arguments(self, parser):
        parser.add_argument('--users', type=int, default=24, help='Number of demo users to create.')
        parser.add_argument('--seed', type=int, default=None, help='RNG seed for reproducible data.')
        parser.add_argument('--fresh', action='store_true', help='Delete existing demo data first.')

    def handle(self, *args, **options):
        rng = random.Random(options.get('seed'))

        if options['fresh']:
            self._flush_demo_data()

        users = self._make_users(options['users'])
        self.stdout.write(self.style.SUCCESS(f'✓ {len(users)} demo users'))

        leagues = self._make_leagues(users, rng)
        self.stdout.write(self.style.SUCCESS(f'✓ {len(leagues)} demo leagues'))

        games = self._make_primetime_week(rng)
        finished = [g for g in games if g.status == 'final']
        self.stdout.write(self.style.SUCCESS(
            f'✓ {len(games)} primetime games ({len(finished)} final, {len(games) - len(finished)} upcoming)'
        ))

        picks = self._make_picks(leagues, games, rng)
        self.stdout.write(self.style.SUCCESS(f'✓ {picks} picks'))

        graded = 0
        for game in finished:
            graded += game.update_pick_results()
        self.stdout.write(self.style.SUCCESS(f'✓ graded {graded} picks for final games'))

        self.stdout.write('\nSample standings for the first league:')
        for row in leagues[0].get_standings()[:5]:
            self.stdout.write(
                f"  {row['user'].username:15} pts={row['total_points']:>2} "
                f"acc={row['accuracy']}% ({row['correct_predictions']}/{row['total_predictions']})"
            )
        self.stdout.write(self.style.SUCCESS('\nDone. Log in with password "demopass123".'))

    # ------------------------------------------------------------------
    def _flush_demo_data(self):
        Pick.objects.filter(user__username__startswith='demo_user_').delete()
        Game.objects.filter(game_id__startswith='demo_game_').delete()
        League.objects.filter(name__startswith='Demo League').delete()
        # Named leagues we own are recreated below; remove membership churn.
        League.objects.filter(name__in=LEAGUE_NAMES).delete()
        from django.contrib.auth import get_user_model
        get_user_model().objects.filter(username__startswith='demo_user_').delete()
        self.stdout.write(self.style.WARNING('Flushed existing demo data.'))

    def _make_users(self, count):
        users = []
        for i in range(count):
            persona = PERSONAS[i] if i < len(PERSONAS) else f'Player{i}'
            user = UserFactory(username=f'demo_user_{i}', team_name=f"{persona}'s Team")
            users.append(user)
        return users

    def _make_leagues(self, users, rng):
        leagues = []
        for idx, size in enumerate(LEAGUE_SIZES):
            if idx >= len(LEAGUE_NAMES):
                break
            size = min(size, len(users))
            members = rng.sample(users, size)
            commissioner = members[0]
            league, _ = League.objects.get_or_create(
                name=LEAGUE_NAMES[idx],
                defaults={'commissioner': commissioner, 'sport': 'NFL', 'is_approved': True},
            )
            for member in members:
                LeagueMembership.objects.get_or_create(user=member, league=league)
            leagues.append(league)
        return leagues

    def _make_primetime_week(self, rng):
        """One realistic primetime slate: TNF, SNF, MNF."""
        today = timezone.now().astimezone(EASTERN).date()
        # Anchor to the most recent Thursday so TNF/SNF are in the past.
        last_thursday = today - timedelta(days=(today.weekday() - 3) % 7)
        slate = [
            ('demo_game_tnf', last_thursday, 20, 15, 'Kansas City Chiefs', 'Buffalo Bills'),
            ('demo_game_snf', last_thursday + timedelta(days=3), 20, 20, 'Philadelphia Eagles', 'Dallas Cowboys'),
            ('demo_game_mnf', last_thursday + timedelta(days=4), 20, 15, 'San Francisco 49ers', 'Detroit Lions'),
        ]
        games = []
        now = timezone.now()
        for game_id, gdate, hour, minute, home, away in slate:
            start = _et(gdate, hour, minute)
            is_past = start < now
            defaults = {
                'season': 2026, 'week': 1, 'game_type': 'regular',
                'start_time': start, 'home_team': home, 'away_team': away,
                'status': 'scheduled',
            }
            if is_past:
                # Give the home favorite a realistic winning edge.
                home_score = rng.choice([20, 24, 27, 31, 34])
                away_score = rng.choice([10, 13, 17, 20, 24])
                defaults.update({'status': 'final', 'home_score': home_score, 'away_score': away_score})
            game, _ = Game.objects.update_or_create(game_id=game_id, defaults=defaults)
            games.append(game)
        return games

    def _make_picks(self, leagues, games, rng):
        """Weighted, imperfect picks: favorites win ~72% of choices and some
        users skip some games (real leagues are never 100% participation)."""
        created = 0
        for league in leagues:
            for member in league.members.all():
                for game in games:
                    if rng.random() > 0.85:  # ~15% of the time a user misses a game
                        continue
                    favorite = game.home_team  # home team is the seeded favorite
                    underdog = game.away_team
                    picked = favorite if rng.random() < 0.72 else underdog
                    _, was_created = Pick.objects.get_or_create(
                        user=member, game=game, league=league,
                        defaults={'picked_team': picked, 'confidence': 1},
                    )
                    if was_created:
                        created += 1
        return created

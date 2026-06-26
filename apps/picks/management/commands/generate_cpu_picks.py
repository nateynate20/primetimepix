from django.core.management.base import BaseCommand
from apps.games.models import Game
from apps.picks.models import CPUPick


class Command(BaseCommand):
    help = 'Generate CPU picks for games based on spread data (favorites)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--week', type=int,
            help='Generate picks for a specific week only',
        )
        parser.add_argument(
            '--all', action='store_true',
            help='Generate picks for all games that do not yet have a CPU pick',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show what would be picked without saving',
        )

    def handle(self, *args, **options):
        week = options.get('week')
        all_games = options.get('all')
        dry_run = options.get('dry_run')

        games_qs = Game.objects.filter(status='scheduled')

        if week:
            games_qs = games_qs.filter(week=week, game_type='regular')
        elif not all_games:
            games_qs = games_qs.filter(game_type='regular')

        # Exclude games that already have a CPU pick
        existing_picks = CPUPick.objects.values_list('game_id', flat=True)
        games_qs = games_qs.exclude(id__in=existing_picks)

        # Only pick primetime games (matches user pick scope)
        games = [g for g in games_qs if g.is_primetime]

        created = 0
        skipped = 0

        for game in games:
            picked_team = self._determine_pick(game)
            if not picked_team:
                skipped += 1
                continue

            if dry_run:
                self.stdout.write(f"  Would pick: {picked_team} for {game}")
                created += 1
                continue

            CPUPick.objects.create(game=game, picked_team=picked_team)
            self.stdout.write(f"  CPU picks: {picked_team} for {game}")
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. Created: {created}, Skipped: {skipped}"
        ))

    def _determine_pick(self, game):
        """Determine which team the CPU picks based on spread data."""
        if game.spread_favorite:
            if game.spread_favorite == 'home':
                return game.home_team
            elif game.spread_favorite == 'away':
                return game.away_team

        # Fallback: pick the home team (NFL home teams win ~57% historically)
        return game.home_team

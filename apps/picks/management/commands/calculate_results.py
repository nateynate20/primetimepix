from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.picks.models import Pick
from apps.games.models import Game

class Command(BaseCommand):
    help = 'Calculate results for finished games'

    def handle(self, *args, **options):
        # Get finished games without calculated picks
        finished_games = Game.objects.filter(
            status='finished',
            pick__is_correct__isnull=True
        ).distinct()

        picks_updated = 0
        for game in finished_games:
            picks = Pick.objects.filter(game=game, is_correct__isnull=True)
            for pick in picks:
                pick.calculate_result()
                picks_updated += 1

        self.stdout.write(
            self.style.SUCCESS(f'Successfully calculated results for {picks_updated} picks')
        )
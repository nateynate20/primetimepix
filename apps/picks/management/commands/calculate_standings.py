from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from game_picks.models import GameSelection, UserRecord, League

class Command(BaseCommand):
    help = 'Calculate and update user standings for all leagues'

    def handle(self, *args, **options):
        # Get all leagues including None (for global/general picks if applicable)
        leagues = list(League.objects.filter(is_approved=True)) + [None]

        for league in leagues:
            if league:
                self.stdout.write(f'Calculating standings for league: {league.name}')
            else:
                self.stdout.write('Calculating general/global standings (no league)')

            # Get all users who have made picks in this league or globally if league is None
            if league:
                user_ids = GameSelection.objects.filter(league=league).values_list('user', flat=True).distinct()
            else:
                user_ids = GameSelection.objects.filter(league__isnull=True).values_list('user', flat=True).distinct()

            users = User.objects.filter(id__in=user_ids)

            for user in users:
                # Count correct and total picks for user in this league
                correct_count = GameSelection.objects.filter(
                    user=user, league=league, is_correct=True
                ).count()

                total_count = GameSelection.objects.filter(
                    user=user, league=league
                ).count()

                accuracy = round((correct_count / total_count) * 100, 2) if total_count else 0

                record, created = UserRecord.objects.get_or_create(user=user, league=league)
                record.correct_predictions = correct_count
                record.total_predictions = total_count
                record.accuracy = accuracy
                record.save()

        self.stdout.write(self.style.SUCCESS('Successfully calculated and updated standings for all leagues'))

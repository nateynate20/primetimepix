from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from game_picks.models import GameSelection, UserRecord

class Command(BaseCommand):
    help = 'Calculate and update user standings'

    def handle(self, *args, **options):
        users = User.objects.all()

        for user in users:
            correct_predictions = GameSelection.objects.filter(user=user, is_correct=True)
            total_predictions = GameSelection.objects.filter(user=user).count()

            # Update user standings
            user_record, created = UserRecord.objects.get_or_create(user=user)
            user_record.correct_predictions = correct_predictions.count()
            user_record.total_predictions = total_predictions
            user_record.save()

        self.stdout.write(self.style.SUCCESS('Successfully calculated and updated standings'))
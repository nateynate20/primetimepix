from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.leagues.models import League, LeagueMembership

class Command(BaseCommand):
    help = 'Create demo leagues for new users'

    def handle(self, *args, **options):
        # Create a public demo league
        demo_league, created = League.objects.get_or_create(
            name="Public NFL Picks League",
            defaults={
                'commissioner': User.objects.filter(is_superuser=True).first(),
                'description': 'Open to all users - compete for the top spot!',
                'is_private': False,
                'is_approved': True,
                'sport': 'NFL'
            }
        )
        
        if created:
            self.stdout.write(f"✓ Created demo league: {demo_league.name}")
        else:
            self.stdout.write(f"✓ Demo league already exists: {demo_league.name}")
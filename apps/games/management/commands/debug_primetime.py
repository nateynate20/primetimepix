from django.core.management.base import BaseCommand
from apps.games.models import Game

class Command(BaseCommand):
    help = 'Debug primetime game detection'

    def handle(self, *args, **options):
        games = Game.objects.all().order_by('start_time')
        self.stdout.write(f"=== PRIMETIME DEBUG ===")
        self.stdout.write(f"Total games in database: {games.count()}")
        
        primetime_count = 0
        for game in games:
            if game.is_primetime:
                primetime_count += 1
                et_time = game.display_time_et
                time_str = et_time.strftime('%A %I:%M %p ET') if et_time else 'TBD'
                self.stdout.write(f"⭐ {game.away_team} @ {game.home_team} - Week {game.week} - {time_str} - {game.primetime_type}")
        
        self.stdout.write(f"\n✅ Found {primetime_count} primetime games out of {games.count()} total games")
        
        if primetime_count == 0 and games.count() > 0:
            self.stdout.write("❌ No primetime games detected. Checking sample games:")
            for game in games[:3]:
                et_time = game.display_time_et
                time_str = et_time.strftime('%A %I:%M %p ET') if et_time else 'TBD'
                self.stdout.write(f"   {game.away_team} @ {game.home_team} - {time_str} - is_primetime: {game.is_primetime}")
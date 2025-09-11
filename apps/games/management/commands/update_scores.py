from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import requests
from apps.games.models import Game
from apps.picks.models import Pick

class Command(BaseCommand):
    help = 'Update scores for recent and live games'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to look back for games (default: 7)',
        )
        parser.add_argument(
            '--live-only',
            action='store_true',
            help='Only update games currently in progress',
        )

    def handle(self, *args, **options):
        days_back = options['days']
        live_only = options['live_only']
        
        # Calculate date range
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Get games to update
        games_query = Game.objects.filter(
            start_time__gte=start_date,
            start_time__lte=end_date
        )
        
        if live_only:
            games_query = games_query.filter(status='in_progress')
        else:
            # Update scheduled games that should have started, in-progress, and recent finals
            games_query = games_query.exclude(status='cancelled')
        
        games_to_update = games_query.order_by('start_time')
        total_games = games_to_update.count()
        
        self.stdout.write(f"Found {total_games} games to check for score updates")
        
        updated_count = 0
        for game in games_to_update:
            try:
                if self._update_game_score(game):
                    updated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ Updated: {game.away_team} @ {game.home_team} - "
                            f"{game.away_score or 0}-{game.home_score or 0} ({game.status})"
                        )
                    )
                    
                    # Update pick results if game is final
                    if game.status == 'final':
                        picks_updated = game.update_pick_results()
                        if picks_updated > 0:
                            self.stdout.write(
                                f"  Updated {picks_updated} pick results"
                            )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"✗ Error updating {game.away_team} @ {game.home_team}: {e}"
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\nScore update complete! Updated {updated_count} of {total_games} games"
            )
        )
    
    def _update_game_score(self, game):
        """Fetch and update score for a single game"""
        # Format date for ESPN API
        game_date = game.start_time.strftime('%Y%m%d')
        
        url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={game_date}"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                return False
            
            data = response.json()
            events = data.get('events', [])
            
            # Find our game in the ESPN data
            for event in events:
                if self._match_game(game, event):
                    return self._update_from_event(game, event)
            
            return False
            
        except Exception as e:
            self.stdout.write(f"API error: {e}")
            return False
    
    def _match_game(self, game, event):
        """Check if ESPN event matches our game"""
        competitors = event.get('competitions', [{}])[0].get('competitors', [])
        if len(competitors) < 2:
            return False
        
        # Get team names from ESPN
        home_team = next((c for c in competitors if c.get('homeAway') == 'home'), {})
        away_team = next((c for c in competitors if c.get('homeAway') == 'away'), {})
        
        home_name = home_team.get('team', {}).get('displayName', '')
        away_name = away_team.get('team', {}).get('displayName', '')
        
        # Match team names (handle slight variations)
        return (home_name in game.home_team or game.home_team in home_name) and \
               (away_name in game.away_team or game.away_team in away_name)
    
    def _update_from_event(self, game, event):
        """Update game with ESPN event data"""
        competition = event.get('competitions', [{}])[0]
        competitors = competition.get('competitors', [])
        
        if len(competitors) < 2:
            return False
        
        # Get scores
        home_team = next((c for c in competitors if c.get('homeAway') == 'home'), {})
        away_team = next((c for c in competitors if c.get('homeAway') == 'away'), {})
        
        old_home_score = game.home_score
        old_away_score = game.away_score
        old_status = game.status
        
        # Update scores
        try:
            game.home_score = int(home_team.get('score', 0))
            game.away_score = int(away_team.get('score', 0))
        except (ValueError, TypeError):
            pass
        
        # Update status
        status_detail = competition.get('status', {}).get('type', {})
        status_name = status_detail.get('name', '').lower()
        
        if 'final' in status_name:
            game.status = 'final'
        elif status_name in ['in', 'in progress', 'halftime']:
            game.status = 'in_progress'
        elif status_name in ['scheduled', 'pre']:
            game.status = 'scheduled'
        
        # Check if anything changed
        if (game.home_score != old_home_score or 
            game.away_score != old_away_score or 
            game.status != old_status):
            game.save()
            return True
        
        return False
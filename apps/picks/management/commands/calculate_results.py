# apps/picks/management/commands/update_pick_results.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.picks.models import Pick
from apps.games.models import Game

class Command(BaseCommand):
    help = 'Update pick results for finished games'

    def add_arguments(self, parser):
        parser.add_argument(
            '--week',
            type=int,
            help='Update results for specific week only',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Update all picks for all finished games',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without saving',
        )

    def handle(self, *args, **options):
        week = options.get('week')
        update_all = options.get('all', False)
        dry_run = options.get('dry_run', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be saved"))
        
        # Get finished games
        finished_games = Game.objects.filter(status='final')
        
        if week:
            finished_games = finished_games.filter(week=week)
            self.stdout.write(f"Updating picks for week {week} finished games...")
        elif update_all:
            self.stdout.write("Updating picks for all finished games...")
        else:
            # Default: update recent games (last 7 days)
            seven_days_ago = timezone.now() - timezone.timedelta(days=7)
            finished_games = finished_games.filter(start_time__gte=seven_days_ago)
            self.stdout.write("Updating picks for recently finished games...")
        
        total_games = finished_games.count()
        total_picks_updated = 0
        games_with_updates = 0
        
        for game in finished_games:
            self.stdout.write(f"\nProcessing: {game.away_team} @ {game.home_team} (Week {game.week})")
            
            # Get winner using the Game model's property
            winner = game.winner
            
            if winner is None:
                self.stdout.write(f"  ⚠️  No winner determined (scores: {game.away_score}-{game.home_score})")
                continue
            
            if winner == 'tie':
                self.stdout.write(f"  ➖ Game ended in a tie: {game.away_score}-{game.home_score}")
            else:
                self.stdout.write(f"  🏆 Winner: {winner} ({game.away_score}-{game.home_score})")
            
            # Get all picks for this game
            picks = Pick.objects.filter(game=game)
            picks_count = picks.count()
            
            if picks_count == 0:
                self.stdout.write(f"  No picks found for this game")
                continue
            
            updated_in_game = 0
            correct_count = 0
            incorrect_count = 0
            push_count = 0
            
            for pick in picks:
                old_correct = pick.is_correct
                old_points = pick.points
                
                if not dry_run:
                    pick.calculate_result()
                    new_correct = pick.is_correct
                    new_points = pick.points
                else:
                    # Simulate the calculation for dry run
                    if winner == 'tie':
                        new_correct = None
                        new_points = 0
                    else:
                        new_correct = (winner == pick.picked_team)
                        new_points = pick.confidence if new_correct else 0
                
                # Track if this pick was updated
                if old_correct != new_correct or old_points != new_points:
                    updated_in_game += 1
                    
                    status_str = "✅ Correct" if new_correct else "❌ Incorrect" if new_correct is False else "➖ Push"
                    self.stdout.write(
                        f"    {pick.user.username}: picked {pick.picked_team} → {status_str} "
                        f"(points: {old_points} → {new_points})"
                    )
                
                # Count results
                if new_correct is True:
                    correct_count += 1
                elif new_correct is False:
                    incorrect_count += 1
                else:
                    push_count += 1
            
            if updated_in_game > 0:
                games_with_updates += 1
                total_picks_updated += updated_in_game
                
            self.stdout.write(
                f"  📊 Results: {correct_count} correct, {incorrect_count} incorrect, "
                f"{push_count} pushes out of {picks_count} picks"
            )
            
            if updated_in_game > 0:
                self.stdout.write(f"  ✓ Updated {updated_in_game} picks")
        
        # Summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS(
            f"Summary: Processed {total_games} games, "
            f"updated {total_picks_updated} picks across {games_with_updates} games"
        ))
        
        if dry_run:
            self.stdout.write(self.style.WARNING(
                "DRY RUN COMPLETE - No changes were saved. "
                "Run without --dry-run to apply changes."
            ))
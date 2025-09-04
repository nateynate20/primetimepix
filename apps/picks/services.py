# apps/picks/services.py
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from typing import List, Dict, Optional
from .models import Pick, UserStats
from apps.games.models import Game
from apps.games.utils import is_primetime_game, get_current_week_dates

User = get_user_model()

class PickService:
    """Service class for handling pick-related business logic"""

    @staticmethod
    def get_user_picks_for_week(user, league=None, week=None, year=None):
        """Get user's picks for a specific week"""
        from apps.games.utils import get_week_date_range
        from datetime import datetime
        
        if not week:
            week = get_current_nfl_week()
        if not year:
            year = timezone.now().year
        
        week_start, week_end = get_week_date_range(year, week)
        week_start_dt = datetime.combine(week_start, datetime.min.time())
        week_end_dt = datetime.combine(week_end, datetime.max.time())
        
        return Pick.objects.filter(
            user=user,
            league=league,
            game__start_time__gte=week_start_dt,
            game__start_time__lte=week_end_dt
        ).select_related('game', 'league')

    @staticmethod
    def get_pickable_games_for_user(user, league=None):
        """Get games that user can still make picks for"""
        from apps.games.utils import NFLScheduleHelper
        
        # Get current week primetime games
        current_week_games = NFLScheduleHelper.get_primetime_games_for_week()
        
        # Filter to only games that can still have picks made
        pickable_games = [game for game in current_week_games if game.can_make_picks()]
        
        return pickable_games

    @staticmethod
    def get_user_pick_status(user, games, league=None):
        """Get user's pick status for a list of games"""
        if not games:
            return {}
        
        existing_picks = Pick.objects.filter(
            user=user,
            league=league,
            game__in=games
        ).select_related('game')
        
        pick_dict = {}
        for pick in existing_picks:
            pick_dict[pick.game.id] = {
                'pick': pick,
                'picked_team': pick.picked_team,
                'picked_home': pick.picked_home_team,
                'confidence': pick.confidence_points,
                'can_update': pick.can_be_updated
            }
        
        return pick_dict

    @staticmethod
    @transaction.atomic
    def save_user_picks(user, picks_data, league=None):
        """
        Save multiple picks for a user
        picks_data format: {game_id: {'team': 'team_name', 'confidence': int}}
        """
        saved_picks = []
        errors = []
        
        for game_id, pick_data in picks_data.items():
            try:
                game = Game.objects.get(id=game_id)
                
                # Validate game can still have picks
                if not game.can_make_picks():
                    errors.append(f"Game {game} has already started")
                    continue
                
                picked_team = pick_data.get('team')
                confidence = pick_data.get('confidence', 1)
                
                # Validate team choice
                if picked_team not in [game.home_team, game.away_team]:
                    errors.append(f"Invalid team selection for {game}")
                    continue
                
                # Create or update pick
                pick, created = Pick.objects.update_or_create(
                    user=user,
                    game=game,
                    league=league,
                    defaults={
                        'picked_team': picked_team,
                        'confidence_points': confidence
                    }
                )
                
                saved_picks.append(pick)
                
            except Game.DoesNotExist:
                errors.append(f"Game with ID {game_id} not found")
            except Exception as e:
                errors.append(f"Error saving pick for game {game_id}: {str(e)}")
        
        return saved_picks, errors

    @staticmethod
    def update_pick_correctness_for_game(game):
        """Update correctness for all picks related to a finished game"""
        if not game.is_finished:
            return
        
        picks = Pick.objects.filter(game=game)
        for pick in picks:
            pick.update_correctness()

    @staticmethod
    def calculate_leaderboard(league=None, limit=None):
        """Calculate and return leaderboard data"""
        stats_query = UserStats.objects.filter(league=league).select_related('user')
        
        if limit:
            stats_query = stats_query[:limit]
        
        leaderboard = []
        for i, stat in enumerate(stats_query, 1):
            leaderboard.append({
                'rank': i,
                'user': stat.user,
                'total_picks': stat.total_picks,
                'correct_picks': stat.correct_picks,
                'wrong_picks': stat.wrong_picks,
                'accuracy': stat.accuracy_percentage,
                'total_points': stat.total_points,
                'current_week_picks': stat.current_week_picks,
                'current_week_correct': stat.current_week_correct,
            })
        
        return leaderboard

class StatsService:
    """Service class for handling statistics and leaderboards"""

    @staticmethod
    def get_user_overall_stats(user):
        """Get user's overall statistics across all leagues"""
        all_picks = Pick.objects.filter(user=user)
        total_picks = all_picks.count()
        correct_picks = all_picks.filter(is_correct=True).count()
        
        return {
            'user': user,
            'total_picks': total_picks,
            'correct_picks': correct_picks,
            'accuracy': (correct_picks / total_picks * 100) if total_picks > 0 else 0,
            'total_points': sum(pick.get_points_earned() for pick in all_picks)
        }

    @staticmethod
    def get_league_stats_summary(league=None):
        """Get summary statistics for a league"""
        if league:
            picks_query = Pick.objects.filter(league=league)
            members_count = league.members.count()
        else:
            picks_query = Pick.objects.filter(league__isnull=True)
            members_count = User.objects.filter(picks__league__isnull=True).distinct().count()
        
        total_picks = picks_query.count()
        correct_picks = picks_query.filter(is_correct=True).count()
        
        return {
            'league': league,
            'total_members': members_count,
            'total_picks': total_picks,
            'correct_picks': correct_picks,
            'overall_accuracy': (correct_picks / total_picks * 100) if total_picks > 0 else 0,
        }

    @staticmethod
    def update_all_user_stats(league=None):
        """Update statistics for all users in a league"""
        if league:
            users = league.members.all()
        else:
            users = User.objects.filter(picks__league__isnull=True).distinct()
        
        for user in users:
            stats, created = UserStats.objects.get_or_create(user=user, league=league)
            stats.update_stats()

    @staticmethod
    def get_weekly_performance(user, league=None, weeks_back=4):
        """Get user's performance over the last few weeks"""
        from apps.games.utils import get_current_nfl_week, get_week_date_range
        from datetime import datetime
        
        current_week = get_current_nfl_week()
        year = timezone.now().year
        
        weekly_data = []
        
        for i in range(weeks_back):
            week_num = current_week - i
            if week_num < 1:
                continue
            
            week_start, week_end = get_week_date_range(year, week_num)
            week_start_dt = datetime.combine(week_start, datetime.min.time())
            week_end_dt = datetime.combine(week_end, datetime.max.time())
            
            week_picks = Pick.objects.filter(
                user=user,
                league=league,
                game__start_time__gte=week_start_dt,
                game__start_time__lte=week_end_dt
            )
            
            total = week_picks.count()
            correct = week_picks.filter(is_correct=True).count()
            points = sum(pick.get_points_earned() for pick in week_picks)
            
            weekly_data.append({
                'week': week_num,
                'total_picks': total,
                'correct_picks': correct,
                'accuracy': (correct / total * 100) if total > 0 else 0,
                'points': points
            })
        
        return list(reversed(weekly_data))  # Most recent first


class GameResultsService:
    """Service for handling game results and updating picks"""

    @staticmethod
    def process_finished_game(game):
        """Process a game that has finished and update all related picks"""
        if not game.is_finished:
            return
        
        # Update all picks for this game
        PickService.update_pick_correctness_for_game(game)
        
        # Update stats for all users who made picks on this game
        picks = Pick.objects.filter(game=game).select_related('user', 'league')
        
        # Get unique user-league combinations
        user_league_combinations = set()
        for pick in picks:
            user_league_combinations.add((pick.user, pick.league))
        
        # Update stats for each combination
        for user, league in user_league_combinations:
            stats, created = UserStats.objects.get_or_create(user=user, league=league)
            stats.update_stats()

    @staticmethod
    def bulk_update_game_results():
        """Update results for all finished games that haven't been processed"""
        finished_games = Game.objects.filter(
            status='final',
            home_score__isnull=False,
            away_score__isnull=False
        )
        
        for game in finished_games:
            GameResultsService.process_finished_game(game)


class PickValidationService:
    """Service for validating picks and pick-related operations"""

    @staticmethod
    def validate_pick_data(game, picked_team, confidence_points=1):
        """Validate pick data before saving"""
        errors = []
        
        # Check if game exists and can have picks made
        if not game.can_make_picks():
            errors.append("This game has already started or finished")
        
        # Validate team selection
        if picked_team not in [game.home_team, game.away_team]:
            errors.append(f"Must pick either {game.home_team} or {game.away_team}")
        
        # Validate confidence points
        if not isinstance(confidence_points, int) or not 1 <= confidence_points <= 10:
            errors.append("Confidence points must be between 1 and 10")
        
        return errors

    @staticmethod
    def can_user_make_picks(user, league=None):
        """Check if user can make picks (e.g., league membership, etc.)"""
        if league and user not in league.members.all():
            return False, "You are not a member of this league"
        
        return True, "OK"

    @staticmethod
    def get_pick_deadline_info(games):
        """Get information about pick deadlines for games"""
        now = timezone.now()
        deadline_info = {}
        
        for game in games:
            time_until_start = game.start_time - now
            hours_until = time_until_start.total_seconds() / 3600
            
            deadline_info[game.id] = {
                'can_pick': game.can_make_picks(),
                'time_until_start': time_until_start,
                'hours_until_start': hours_until,
                'deadline_passed': not game.can_make_picks()
            }
        
        return deadline_info
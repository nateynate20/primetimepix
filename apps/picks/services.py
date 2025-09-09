# apps/picks/services.py
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Sum, Count, Q
from typing import List, Dict, Optional
from .models import Pick, UserStats
from apps.games.models import Game

User = get_user_model()

class PickService:
    """Service class for handling pick-related business logic"""

    @staticmethod
    def get_user_pick_status(user, games, league=None):
        """Get user's pick status for a list of games"""
        if not games:
            return {}
        
        game_ids = [game.id for game in games]
        existing_picks = Pick.objects.filter(
            user=user,
            league=league,
            game_id__in=game_ids
        ).select_related('game')
        
        # Return picks indexed by game.id, with the Pick object directly
        pick_dict = {}
        for pick in existing_picks:
            pick_dict[pick.game.id] = pick
        
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
                    errors.append(f"Picks are closed for {game.away_team} @ {game.home_team}")
                    continue
                
                picked_team = pick_data.get('team')
                confidence = pick_data.get('confidence', 1)
                
                # Validate team choice
                if picked_team not in [game.home_team, game.away_team]:
                    errors.append(f"Invalid team selection for {game.away_team} @ {game.home_team}")
                    continue
                
                # Create or update pick
                pick, created = Pick.objects.update_or_create(
                    user=user,
                    game=game,
                    league=league,
                    defaults={
                        'picked_team': picked_team,
                        'confidence': confidence,
                        'points': confidence  # Initial points = confidence
                    }
                )
                
                saved_picks.append(pick)
                
            except Game.DoesNotExist:
                errors.append(f"Game {game_id} not found")
            except Exception as e:
                errors.append(f"Error saving pick for game {game_id}: {str(e)}")
        
        return saved_picks, errors

    @staticmethod
    def calculate_leaderboard(league=None, limit=100):
        """Calculate and return leaderboard data in format expected by templates"""
        if league:
            # League-specific leaderboard
            picks_filter = Pick.objects.filter(league=league, is_correct__isnull=False)
            users = User.objects.filter(
                pick__league=league,
                pick__is_correct__isnull=False
            ).distinct()
        else:
            # Overall leaderboard
            picks_filter = Pick.objects.filter(league__isnull=True, is_correct__isnull=False)
            users = User.objects.filter(
                pick__league__isnull=True,
                pick__is_correct__isnull=False
            ).distinct()
        
        leaderboard = []
        
        for user in users:
            user_picks = picks_filter.filter(user=user)
            total_picks = user_picks.count()
            
            if total_picks == 0:
                continue
            
            correct_picks = user_picks.filter(is_correct=True).count()
            total_points = user_picks.aggregate(Sum('points'))['points__sum'] or 0
            win_percentage = (correct_picks / total_picks) * 100 if total_picks > 0 else 0
            
            # Get primetime stats
            primetime_picks = user_picks.filter(game__is_primetime=True)
            primetime_total = primetime_picks.count()
            primetime_correct = primetime_picks.filter(is_correct=True).count()
            primetime_percentage = (primetime_correct / primetime_total * 100) if primetime_total > 0 else 0
            
            leaderboard.append({
                'user': user,
                'total_predictions': total_picks,
                'correct_predictions': correct_picks,
                'accuracy': round(win_percentage, 1),
                'total_points': total_points,
                'primetime_picks': primetime_total,
                'primetime_correct': primetime_correct,
                'primetime_percentage': round(primetime_percentage, 1),
            })
        
        # Sort by accuracy (desc), then by total points (desc), then by total picks (desc)
        leaderboard.sort(
            key=lambda x: (x['accuracy'], x['total_points'], x['total_predictions']),
            reverse=True
        )
        
        # Add rank
        for i, entry in enumerate(leaderboard[:limit], 1):
            entry['rank'] = i
        
        return leaderboard[:limit]

    @staticmethod
    def get_user_stats(user, league=None):
        """Get comprehensive stats for a user - format expected by templates"""
        if league:
            picks = Pick.objects.filter(user=user, league=league, is_correct__isnull=False)
        else:
            picks = Pick.objects.filter(user=user, is_correct__isnull=False)
        
        total_picks = picks.count()
        if total_picks == 0:
            return {
                'total_picks': 0,
                'correct_picks': 0,
                'win_percentage': 0,
                'total_points': 0,
                'primetime_picks': 0,
                'primetime_correct': 0,
                'primetime_percentage': 0,
                'current_streak': 0
            }
        
        correct_picks = picks.filter(is_correct=True).count()
        total_points = picks.aggregate(Sum('points'))['points__sum'] or 0
        win_percentage = (correct_picks / total_picks) * 100
        
        # Primetime stats
        primetime_picks = picks.filter(game__is_primetime=True)
        primetime_total = primetime_picks.count()
        primetime_correct = primetime_picks.filter(is_correct=True).count()
        primetime_percentage = (primetime_correct / primetime_total * 100) if primetime_total > 0 else 0
        
        # Current streak
        recent_picks = picks.order_by('-created_at')[:10]
        current_streak = 0
        if recent_picks:
            last_result = recent_picks[0].is_correct
            for pick in recent_picks:
                if pick.is_correct == last_result:
                    if pick.is_correct:
                        current_streak += 1
                    else:
                        current_streak -= 1
                else:
                    break
        
        return {
            'total_picks': total_picks,
            'correct_picks': correct_picks,
            'win_percentage': round(win_percentage, 1),
            'total_points': total_points,
            'primetime_picks': primetime_total,
            'primetime_correct': primetime_correct,
            'primetime_percentage': round(primetime_percentage, 1),
            'current_streak': current_streak
        }

    @staticmethod
    def update_pick_correctness_for_game(game):
        """Update correctness for all picks related to a finished game"""
        if not game.is_finished:
            return 0
        
        picks = Pick.objects.filter(game=game)
        updated_count = 0
        for pick in picks:
            old_correct = pick.is_correct
            pick.calculate_result()
            if old_correct != pick.is_correct:
                updated_count += 1
        
        return updated_count

    @staticmethod
    def update_all_pick_results():
        """Update results for all picks where games are finished"""
        finished_games = Game.objects.filter(status='final')
        updated_count = 0
        
        for game in finished_games:
            updated_count += PickService.update_pick_correctness_for_game(game)
        
        return updated_count


class StatsService:
    """Service class for handling statistics and leaderboards"""

    @staticmethod
    def get_user_overall_stats(user):
        """Get user's overall statistics across all leagues"""
        return PickService.get_user_stats(user, league=None)

    @staticmethod
    def get_league_standings_data(league):
        """Get standings data formatted for league standings template"""
        if not league:
            return []
        
        members = league.members.all()
        standings = []
        
        for member in members:
            picks = Pick.objects.filter(user=member, league=league, is_correct__isnull=False)
            total_picks = picks.count()
            correct_picks = picks.filter(is_correct=True).count()
            total_points = picks.aggregate(Sum('points'))['points__sum'] or 0
            
            if total_picks > 0:
                percentage = (correct_picks / total_picks) * 100
            else:
                percentage = 0
            
            standings.append({
                'username': member.username,
                'user': member,
                'points': total_points,
                'correct': correct_picks,
                'total': total_picks,
                'percentage': round(percentage, 1)
            })
        
        # Sort by points (desc), then by percentage (desc), then by correct picks (desc)
        standings.sort(
            key=lambda x: (x['points'], x['percentage'], x['correct']),
            reverse=True
        )
        
        return standings
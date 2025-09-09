# apps/picks/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Count, Q, Sum
from apps.games.models import Game
from apps.leagues.models import League

User = get_user_model()

class Pick(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    league = models.ForeignKey(League, on_delete=models.CASCADE, null=True, blank=True)
    picked_team = models.CharField(max_length=50)
    confidence = models.IntegerField(default=1)  # ADD THIS FIELD
    is_correct = models.BooleanField(null=True, blank=True)
    points = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'game', 'league']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['game', 'is_correct']),
            models.Index(fields=['league', 'created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.picked_team} ({self.game})"

    def calculate_result(self):
        """Calculate if this pick was correct based on game result"""
        if not self.game.is_finished:
            return None
        
        # Use the Game model's winner property
        winner = self.game.winner
        if winner is None:
            return None
            
        # Handle tie games - traditionally these are considered "pushes" 
        if winner == 'tie':
            self.is_correct = None  # Neither correct nor incorrect
            self.points = 0  # No points awarded for ties
        else:
            self.is_correct = (winner == self.picked_team)
            # Calculate points based on correctness and confidence
            if self.is_correct:
                self.points = self.confidence
            else:
                self.points = 0
            
        self.save()
        return self.is_correct

    @property
    def is_primetime_pick(self):
        """Check if this pick is for a primetime game"""
        return self.game.is_primetime if hasattr(self.game, 'is_primetime') else False

    @property
    def result_status(self):
        """Get human-readable result status"""
        if self.is_correct is None:
            if self.game.is_finished and self.game.winner == 'tie':
                return "Push (Tie)"
            return "Pending"
        elif self.is_correct:
            return "Correct"
        else:
            return "Incorrect"

    @property
    def points_earned(self):
        """Get points earned for this pick"""
        if self.is_correct is True:
            return self.confidence
        else:
            return 0


class UserStats(models.Model):
    """Model to track user picking statistics"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='pick_stats')
    total_picks = models.IntegerField(default=0)
    correct_picks = models.IntegerField(default=0)
    win_percentage = models.FloatField(default=0.0)
    current_streak = models.IntegerField(default=0)
    best_streak = models.IntegerField(default=0)
    primetime_picks = models.IntegerField(default=0)
    primetime_correct = models.IntegerField(default=0)
    primetime_win_percentage = models.FloatField(default=0.0)
    total_points = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "User Stats"
        verbose_name_plural = "User Stats"
        indexes = [
            models.Index(fields=['win_percentage']),
            models.Index(fields=['total_points']),
            models.Index(fields=['best_streak']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.win_percentage:.1f}% ({self.total_picks} picks)"
    
    def update_stats(self):
        """Update user statistics based on their picks"""
        user_picks = Pick.objects.filter(user=self.user, is_correct__isnull=False)
        self.total_picks = user_picks.count()
        
        # Count correct picks
        correct_picks_qs = user_picks.filter(is_correct=True)
        self.correct_picks = correct_picks_qs.count()
        
        # Calculate win percentage
        if self.total_picks > 0:
            self.win_percentage = (self.correct_picks / self.total_picks) * 100
        else:
            self.win_percentage = 0.0
        
        # Calculate total points
        self.total_points = Pick.objects.filter(user=self.user).aggregate(
            total=Sum('points')
        )['total'] or 0
        
        # Update primetime stats using the game's is_primetime property
        try:
            primetime_picks = user_picks.filter(game__is_primetime=True)
            self.primetime_picks = primetime_picks.count()
            self.primetime_correct = primetime_picks.filter(is_correct=True).count()
            
            if self.primetime_picks > 0:
                self.primetime_win_percentage = (self.primetime_correct / self.primetime_picks) * 100
            else:
                self.primetime_win_percentage = 0.0
        except Exception:
            # Fallback if primetime filtering fails
            self.primetime_picks = 0
            self.primetime_correct = 0
            self.primetime_win_percentage = 0.0
        
        # Calculate current streak
        self.current_streak = self._calculate_current_streak()
        
        # Update best streak
        current_best = self._calculate_best_streak()
        if current_best > self.best_streak:
            self.best_streak = current_best
        
        self.save()
    
    def _calculate_current_streak(self):
        """Calculate current winning/losing streak"""
        recent_picks = Pick.objects.filter(
            user=self.user,
            is_correct__isnull=False
        ).order_by('-created_at')[:20]  # Check last 20 picks
        
        if not recent_picks:
            return 0
        
        streak = 0
        last_result = None
        
        for pick in recent_picks:
            if last_result is None:
                last_result = pick.is_correct
                streak = 1 if pick.is_correct else -1
            elif pick.is_correct == last_result:
                if pick.is_correct:
                    streak += 1
                else:
                    streak -= 1
            else:
                break
        
        return streak
    
    def _calculate_best_streak(self):
        """Calculate the best winning streak ever"""
        picks = Pick.objects.filter(
            user=self.user,
            is_correct__isnull=False
        ).order_by('created_at')
        
        if not picks:
            return 0
        
        current_streak = 0
        best_streak = 0
        
        for pick in picks:
            if pick.is_correct:
                current_streak += 1
                best_streak = max(best_streak, current_streak)
            else:
                current_streak = 0
        
        return best_streak
    
    @classmethod
    def get_or_create_for_user(cls, user):
        """Get or create UserStats for a user"""
        stats, created = cls.objects.get_or_create(
            user=user,
            defaults={
                'total_picks': 0,
                'correct_picks': 0,
                'win_percentage': 0.0,
                'current_streak': 0,
                'best_streak': 0,
                'primetime_picks': 0,
                'primetime_correct': 0,
                'primetime_win_percentage': 0.0,
                'total_points': 0,
            }
        )
        if created:
            stats.update_stats()
        return stats
    
    def get_rank(self):
        """Get user's rank based on win percentage"""
        better_users = UserStats.objects.filter(
            win_percentage__gt=self.win_percentage,
            total_picks__gte=5  # Minimum picks to be ranked
        ).count()
        return better_users + 1


class LeagueStats(models.Model):
    """Track user statistics within specific leagues"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    league = models.ForeignKey(League, on_delete=models.CASCADE)
    total_picks = models.IntegerField(default=0)
    correct_picks = models.IntegerField(default=0)
    win_percentage = models.FloatField(default=0.0)
    total_points = models.IntegerField(default=0)
    rank = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'league']
        verbose_name = "League Stats"
        verbose_name_plural = "League Stats"
        indexes = [
            models.Index(fields=['league', 'win_percentage']),
            models.Index(fields=['league', 'total_points']),
        ]
    
    def __str__(self):
        return f"{self.user.username} in {self.league.name} - {self.win_percentage:.1f}%"
    
    def update_league_stats(self):
        """Update statistics for this user in this league"""
        league_picks = Pick.objects.filter(
            user=self.user, 
            league=self.league,
            is_correct__isnull=False
        )
        self.total_picks = league_picks.count()
        self.correct_picks = league_picks.filter(is_correct=True).count()
        
        if self.total_picks > 0:
            self.win_percentage = (self.correct_picks / self.total_picks) * 100
        else:
            self.win_percentage = 0.0
        
        self.total_points = Pick.objects.filter(
            user=self.user, 
            league=self.league
        ).aggregate(total=Sum('points'))['total'] or 0
        
        self.save()
    
    @classmethod
    def get_or_create_for_user_league(cls, user, league):
        """Get or create LeagueStats for a user in a league"""
        stats, created = cls.objects.get_or_create(
            user=user,
            league=league,
            defaults={
                'total_picks': 0,
                'correct_picks': 0,
                'win_percentage': 0.0,
                'total_points': 0,
                'rank': 0,
            }
        )
        if created:
            stats.update_league_stats()
        return stats
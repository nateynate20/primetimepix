# apps/picks/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

User = get_user_model()

class PickManager(models.Manager):
    def for_user_and_league(self, user, league=None):
        """Get picks for a specific user and league"""
        return self.get_queryset().filter(user=user, league=league)
    
    def correct_picks(self):
        """Get only correct picks"""
        return self.get_queryset().filter(is_correct=True)
    
    def for_current_week(self):
        """Get picks for the current NFL week"""
        from apps.games.utils import get_current_nfl_week, get_week_date_range
        from datetime import datetime
        
        week = get_current_nfl_week()
        year = timezone.now().year
        week_start, week_end = get_week_date_range(year, week)
        
        week_start_dt = datetime.combine(week_start, datetime.min.time())
        week_end_dt = datetime.combine(week_end, datetime.max.time())
        
        return self.get_queryset().filter(
            game__start_time__gte=week_start_dt,
            game__start_time__lte=week_end_dt
        )

class Pick(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='picks')
    game = models.ForeignKey('games.Game', on_delete=models.CASCADE, related_name='picks')
    league = models.ForeignKey('leagues.League', on_delete=models.CASCADE, 
                              null=True, blank=True, related_name='picks')
    picked_team = models.CharField(max_length=100)
    confidence_points = models.IntegerField(default=1, help_text="Confidence level (1-10)")
    is_correct = models.BooleanField(null=True, blank=True)  # Set after game ends
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PickManager()

    class Meta:
        unique_together = ('user', 'game', 'league')
        ordering = ['-submitted_at']
        verbose_name = "Pick"
        verbose_name_plural = "Picks"

    def clean(self):
        """Validate the pick"""
        super().clean()
        
        # Ensure picked team is one of the game teams
        if self.picked_team not in [self.game.home_team, self.game.away_team]:
            raise ValidationError(
                f"Picked team '{self.picked_team}' must be either "
                f"'{self.game.home_team}' or '{self.game.away_team}'"
            )
        
        # Ensure pick is made before game starts
        if self.game and not self.game.can_make_picks():
            raise ValidationError("Cannot make picks for games that have already started or finished.")
        
        # Validate confidence points
        if not 1 <= self.confidence_points <= 10:
            raise ValidationError("Confidence points must be between 1 and 10.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def picked_home_team(self):
        """Returns True if user picked the home team"""
        return self.picked_team == self.game.home_team

    @property
    def picked_away_team(self):
        """Returns True if user picked the away team"""
        return self.picked_team == self.game.away_team

    @property
    def can_be_updated(self):
        """Check if pick can still be updated"""
        return self.game.can_make_picks()

    def update_correctness(self):
        """Update the is_correct field based on game result"""
        if not self.game.is_finished:
            self.is_correct = None
        else:
            winning_team = self.game.get_winning_team()
            if winning_team == 'TIE':
                self.is_correct = None  # Or handle ties based on your rules
            else:
                self.is_correct = (self.picked_team == winning_team)
        
        self.save(update_fields=['is_correct'])

    def get_points_earned(self):
        """Calculate points earned for this pick"""
        if self.is_correct is None:
            return 0  # Game not finished or was a tie
        
        return self.confidence_points if self.is_correct else 0

    def __str__(self):
        league_info = f" in {self.league.name}" if self.league else " (general)"
        status = ""
        if self.is_correct is True:
            status = " ✓"
        elif self.is_correct is False:
            status = " ✗"
        
        return f"{self.user.username} picked {self.picked_team} for {self.game}{league_info}{status}"


class UserStats(models.Model):
    """Model to cache user statistics for performance"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pick_stats')
    league = models.ForeignKey('leagues.League', on_delete=models.CASCADE, 
                              null=True, blank=True, related_name='user_stats')
    
    # Stats
    total_picks = models.IntegerField(default=0)
    correct_picks = models.IntegerField(default=0)
    total_points = models.IntegerField(default=0)  # For confidence points
    accuracy_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    # Week-specific tracking
    current_week_picks = models.IntegerField(default=0)
    current_week_correct = models.IntegerField(default=0)
    
    # Rankings
    overall_rank = models.IntegerField(null=True, blank=True)
    league_rank = models.IntegerField(null=True, blank=True)
    
    # Timestamps
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'league')
        ordering = ['-total_points', '-accuracy_percentage', 'user__username']
        verbose_name = "User Stats"
        verbose_name_plural = "User Stats"

    def update_stats(self):
        """Recalculate and update all stats"""
        picks_query = Pick.objects.for_user_and_league(self.user, self.league)
        
        self.total_picks = picks_query.count()
        self.correct_picks = picks_query.correct_picks().count()
        self.total_points = sum(pick.get_points_earned() for pick in picks_query)
        
        if self.total_picks > 0:
            self.accuracy_percentage = (self.correct_picks / self.total_picks) * 100
        else:
            self.accuracy_percentage = 0.00
        
        # Update current week stats
        current_week_picks = picks_query.for_current_week()
        self.current_week_picks = current_week_picks.count()
        self.current_week_correct = current_week_picks.correct_picks().count()
        
        self.save()

    @property
    def wrong_picks(self):
        """Calculate wrong picks"""
        return self.total_picks - self.correct_picks

    def __str__(self):
        league_info = f" ({self.league.name})" if self.league else " (general)"
        return f"{self.user.username}{league_info}: {self.correct_picks}/{self.total_picks} ({self.accuracy_percentage}%)"


# Signal to update stats when picks are saved
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=Pick)
def update_user_stats_on_pick_save(sender, instance, **kwargs):
    """Update user stats when a pick is saved"""
    stats, created = UserStats.objects.get_or_create(
        user=instance.user,
        league=instance.league
    )
    stats.update_stats()

@receiver(post_delete, sender=Pick)
def update_user_stats_on_pick_delete(sender, instance, **kwargs):
    """Update user stats when a pick is deleted"""
    try:
        stats = UserStats.objects.get(user=instance.user, league=instance.league)
        stats.update_stats()
    except UserStats.DoesNotExist:
        pass
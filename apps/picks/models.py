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
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'game', 'league'],
                name='unique_pick_with_league',
                condition=models.Q(league__isnull=False),
            ),
            models.UniqueConstraint(
                fields=['user', 'game'],
                name='unique_pick_without_league',
                condition=models.Q(league__isnull=True),
            ),
        ]
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
        """Update user statistics, counted per distinct GAME (not per pick row).

        Picks live per-league, so a member in several leagues picks the same
        matchup multiple times. Counting raw pick rows double/triple-counts one
        game — which, before this fix, could show a 3-game win streak after a
        single game finished. We collapse to one result per game first.
        """
        results = self._game_results()  # chronological, one entry per game

        self.total_picks = len(results)
        self.correct_picks = sum(1 for r in results if r['correct'])
        self.win_percentage = (
            (self.correct_picks / self.total_picks) * 100 if self.total_picks else 0.0
        )
        # Points from resolved, correct games only.
        self.total_points = sum(r['points'] for r in results if r['correct'])

        primetime = [r for r in results if r['primetime']]
        self.primetime_picks = len(primetime)
        self.primetime_correct = sum(1 for r in primetime if r['correct'])
        self.primetime_win_percentage = (
            (self.primetime_correct / self.primetime_picks) * 100
            if self.primetime_picks else 0.0
        )

        outcomes = [r['correct'] for r in results]
        self.current_streak = self._current_streak(outcomes)
        # Best is the true all-time max over full history, so set it directly —
        # a previously stored (inflated) value must be allowed to correct down.
        self.best_streak = self._best_streak(outcomes)

        self.save()

    def _game_results(self):
        """One result per distinct game the user has a graded pick for,
        ordered chronologically by kickoff.

        Multi-league members pick the same matchup in each league; we keep a
        single representative per game (they normally agree since it's the same
        game) so stats/streaks reflect games, not league memberships.
        """
        picks = Pick.objects.filter(
            user=self.user, is_correct__isnull=False
        ).select_related('game')

        by_game = {}
        for p in picks:
            if p.game_id not in by_game:
                by_game[p.game_id] = p

        reps = sorted(
            by_game.values(),
            key=lambda p: (p.game.start_time or p.created_at),
        )
        return [
            {
                'correct': bool(p.is_correct),
                'points': p.points or 0,
                'primetime': p.game.is_primetime,
            }
            for p in reps
        ]

    @staticmethod
    def _best_streak(outcomes):
        """Longest run of consecutive wins over an ordered list of booleans."""
        best = cur = 0
        for won in outcomes:
            if won:
                cur += 1
                best = max(best, cur)
            else:
                cur = 0
        return best

    @staticmethod
    def _current_streak(outcomes):
        """Signed current streak: +N wins / -N losses from the most recent game."""
        streak = 0
        last = None
        for won in reversed(outcomes):
            if last is None:
                last = won
                streak = 1 if won else -1
            elif won == last:
                streak += 1 if won else -1
            else:
                break
        return streak
    
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


class CPUPick(models.Model):
    """CPU opponent picks based on spread favorites from ESPN."""
    game = models.OneToOneField(Game, on_delete=models.CASCADE, related_name='cpu_pick')
    picked_team = models.CharField(max_length=50)
    is_correct = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_correct']),
        ]

    def __str__(self):
        return f"CPU picked {self.picked_team} ({self.game})"

    def resolve(self):
        """Resolve this CPU pick based on game result."""
        if not self.game.is_finished:
            return None
        winner = self.game.winner
        if winner is None or winner == 'tie':
            self.is_correct = None
        else:
            self.is_correct = (winner == self.picked_team)
        self.save()
        return self.is_correct


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
        
        # Points come from resolved, correct picks only (unresolved picks keep
        # the default points=1 and would otherwise inflate the total).
        self.total_points = league_picks.filter(is_correct=True).aggregate(
            total=Sum('points')
        )['total'] or 0
        
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
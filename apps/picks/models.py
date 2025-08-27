# apps/picks/models.py
from django.db import models
from django.contrib.auth import get_user_model
from apps.games.models import Game
from apps.leagues.models import League

User = get_user_model()

class Pick(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    league = models.ForeignKey(League, on_delete=models.CASCADE, null=True, blank=True)  # Add this field
    picked_team = models.CharField(max_length=100)
    is_correct = models.BooleanField(null=True, blank=True)  # Set after game ends
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        league_info = f" in {self.league.name}" if self.league else " (general)"
        return f"{self.user.username} picked {self.picked_team} for {self.game}{league_info}"

    class Meta:
        unique_together = ('user', 'game', 'league')  # Updated to include league
        ordering = ['-submitted_at']
        verbose_name = "Pick"
        verbose_name_plural = "Picks"
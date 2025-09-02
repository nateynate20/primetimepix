# apps/picks/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.games.models import Game
from apps.leagues.models import League

User = get_user_model()

class Pick(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    league = models.ForeignKey(League, on_delete=models.CASCADE, null=True)
    picked_team = models.CharField(max_length=50)
    is_correct = models.BooleanField(null=True)
    points = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'game', 'league']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.picked_team} ({self.game})"

    def calculate_result(self):
        if not self.game.is_finished:
            return None
        
        winner = None
        if self.game.home_score > self.game.away_score:
            winner = self.game.home_team
        elif self.game.away_score > self.game.home_score:
            winner = self.game.away_team
            
        self.is_correct = winner == self.picked_team
        self.save()
        return self.is_correct
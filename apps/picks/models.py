
from django.db import models
from django.contrib.auth import get_user_model
from apps.games.models import Game

User = get_user_model()

class Pick(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    picked_team = models.CharField(max_length=100)
    is_correct = models.BooleanField(null=True, blank=True)  # Set after game ends
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} picked {self.picked_team} for {self.game}"

    class Meta:
        unique_together = ('user', 'game')  # Prevent duplicate picks per user/game
        ordering = ['-submitted_at']
        verbose_name = "Pick"
        verbose_name_plural = "Picks"

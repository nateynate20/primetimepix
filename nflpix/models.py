#nflpix/models.py
from django.conf import settings
from django.db import models




class GameSelection(models.Model):
    game = models.ForeignKey('nfl_schedule.NFLGame', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    predicted_winner = models.CharField(max_length=50)
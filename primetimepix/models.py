from django.db import models
from django.contrib.auth.models import User

class Player(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    team_name = models.CharField(max_length=100)
    # add other fields as needed

    def __str__(self):
        return self.username

class LeagueCreationRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    league_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.league_name} requested by {self.user.username}"

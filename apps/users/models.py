#apps/users/models.py
from django.contrib.auth.models import User
from django.db import models

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    team_name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"{self.user.username}'s profile"

<<<<<<< HEAD
#apps/leagues/models.py
=======
# apps/leagues/models.py

>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class League(models.Model):
    name = models.CharField(max_length=100)
    commissioner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leagues_owned')
    sport = models.CharField(max_length=10, choices=[('NFL', 'NFL'), ('NBA', 'NBA')], default='NFL')
    created_at = models.DateTimeField(auto_now_add=True)
    is_private = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False)  # New field to track approval status

    members = models.ManyToManyField(
        User,
        through='LeagueMembership',
        related_name='leagues'
    )

    def __str__(self):
        return f"{self.name} ({self.sport})"


class LeagueMembership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    league = models.ForeignKey(League, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'league')
        verbose_name = "League Membership"
        verbose_name_plural = "League Memberships"

    def __str__(self):
        return f"{self.user.username} in {self.league.name}"


class LeagueCreationRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    league_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)

    def __str__(self):
        return f"League Creation Request by {self.user.username}: {self.league_name}"


class LeagueJoinRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    league = models.ForeignKey(League, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'league')

    def __str__(self):
        return f"Join Request: {self.user.username} → {self.league.name}"

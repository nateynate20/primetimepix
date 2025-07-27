from django.db import models
from django.contrib.auth.models import User

class League(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    is_approved = models.BooleanField(default=False)  # Whether league is approved by admin
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_leagues'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    members = models.ManyToManyField(
        User,
        related_name='leagues',
        blank=True,
        help_text='Users who are members of this league'
    )

    def __str__(self):
        return self.name

class GameSelection(models.Model):
    game = models.ForeignKey('nfl_schedule.NFLGame', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    predicted_winner = models.CharField(max_length=50)
    is_correct = models.BooleanField(default=False)
    league = models.ForeignKey(
        League,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text='The league this prediction belongs to'
    )

class UserRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    correct_predictions = models.IntegerField(default=0)
    total_predictions = models.IntegerField(default=0)
    league = models.ForeignKey(
        League,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='The league this record belongs to'
    )

    def __str__(self):
        return f"{self.user.username}'s Record"

class LeagueCreationRequest(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='league_creation_requests'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(
        null=True,
        blank=True,
        help_text='None = pending, True = approved, False = denied'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_league_requests'
    )

    def __str__(self):
        return f"Request by {self.user.username} to create league '{self.name}'"

class LeagueJoinRequest(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='league_join_requests'
    )
    league = models.ForeignKey(
        League,
        on_delete=models.CASCADE,
        related_name='join_requests'
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(
        null=True,
        blank=True,
        help_text='None = pending, True = approved, False = denied'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_join_requests'
    )

    def __str__(self):
        return f"Request by {self.user.username} to join league '{self.league.name}'"

#apps/users/models.py
from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    team_name = models.CharField(max_length=100, unique=True)
    password_reset_sent = models.BooleanField(default=False)
    cpu_challenge_active = models.BooleanField(default=False)
    email_reminders_enabled = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username}'s profile"


class Notification(models.Model):
    """In-app notifications for users."""
    NOTIF_TYPES = [
        ('pick_reminder', 'Pick Reminder'),
        ('result', 'Game Result'),
        ('general', 'General'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIF_TYPES, default='general')
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=200, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.username}: {self.title}"


class ReminderLog(models.Model):
    """Track sent reminders to prevent duplicates.

    Per-game reminders (day_before / morning_of / hours_before) set `game`, so
    each specific primetime game is deduped independently. The weekly
    "make your picks" reminder is week-level and leaves `game` null.
    """
    REMINDER_TYPES = [
        ('weekly', 'Weekly Slate'),
        ('day_before', 'Day Before'),
        ('morning_of', 'Morning Of'),
        ('hours_before', 'Hours Before Kickoff'),
        ('recap', 'Weekly Recap'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reminder_logs')
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPES)
    game = models.ForeignKey(
        'games.Game', on_delete=models.CASCADE, null=True, blank=True,
        related_name='reminder_logs',
        help_text='The specific game this reminder was for (null for weekly).',
    )
    week = models.IntegerField()
    season = models.IntegerField()
    sent_at = models.DateTimeField(auto_now_add=True)
    sent_via_email = models.BooleanField(default=False)
    sent_via_app = models.BooleanField(default=False)

    class Meta:
        unique_together = ['user', 'reminder_type', 'week', 'season', 'game']
        ordering = ['-sent_at']

    def __str__(self):
        scope = f"game {self.game_id}" if self.game_id else f"Week {self.week}"
        return f"{self.user.username} - {self.reminder_type} - {scope}"

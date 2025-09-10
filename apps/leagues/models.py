# apps/leagues/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

User = get_user_model()

class League(models.Model):
    name = models.CharField(max_length=100)
    commissioner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leagues_owned')
    sport = models.CharField(max_length=10, choices=[('NFL', 'NFL'), ('NBA', 'NBA')], default='NFL')
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_private = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=True)

    members = models.ManyToManyField(
        User,
        through='LeagueMembership',
        related_name='leagues'
    )

    def __str__(self):
        return f"{self.name} ({self.sport})"

    class Meta:
        ordering = ['-created_at']

    # Removed the member_count property to avoid conflicts
    # Now use annotation in views: .annotate(member_count=Count('members'))
    
    def get_member_count(self):
        """Use this method when you need member count without annotation"""
        return self.members.count()

    def get_standings(self):
        """Get league standings with user statistics"""
        from apps.picks.models import Pick
        from django.db.models import Count, Sum, Case, When, F, FloatField
        
        # Get all members and their pick statistics for this league
        standings = []
        
        for member in self.members.all():
            # Get picks for this user in this league
            user_picks = Pick.objects.filter(user=member, league=self)
            total_picks = user_picks.count()
            
            if total_picks == 0:
                standings.append({
                    'user': member,
                    'total_predictions': 0,
                    'correct_predictions': 0,
                    'accuracy': 0,
                    'total_points': 0,
                })
                continue
            
            # Calculate statistics
            correct_picks = user_picks.filter(is_correct=True).count()
            total_points = user_picks.aggregate(
                total=Sum('points')
            )['total'] or 0
            
            accuracy = round((correct_picks / total_picks) * 100, 1) if total_picks > 0 else 0
            
            standings.append({
                'user': member,
                'total_predictions': total_picks,
                'correct_predictions': correct_picks,
                'accuracy': accuracy,
                'total_points': total_points,
            })
        
        # Sort by total points (desc), then by accuracy (desc), then by correct picks (desc)
        standings.sort(
            key=lambda x: (x['total_points'], x['accuracy'], x['correct_predictions']),
            reverse=True
        )
        
        return standings


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
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='league_creation_requests'
    )
    league_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.league_name} - {self.user.username}"

    class Meta:
        ordering = ['-created_at']


class LeagueJoinRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    league = models.ForeignKey(League, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'league')
        ordering = ['-created_at']

    def __str__(self):
        return f"Join Request: {self.user.username} → {self.league.name}"


# Signal to automatically add commissioner as member when league is created
@receiver(post_save, sender=League)
def add_commissioner_as_member(sender, instance, created, **kwargs):
    """Automatically add the commissioner as a member when a league is created"""
    if created:
        LeagueMembership.objects.get_or_create(
            user=instance.commissioner,
            league=instance
        )
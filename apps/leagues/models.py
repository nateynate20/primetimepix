# apps/leagues/models.py
import secrets
import uuid

from django.db import models
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

User = get_user_model()

# Unambiguous alphabet for shareable codes (no 0/O, 1/I, etc.)
JOIN_CODE_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'


def generate_join_code(length=8):
    return ''.join(secrets.choice(JOIN_CODE_ALPHABET) for _ in range(length))

class League(models.Model):
    name = models.CharField(max_length=100)
    commissioner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leagues_owned')
    co_commissioners = models.ManyToManyField(
        User,
        blank=True,
        related_name='leagues_co_commissioned',
        help_text='Members who can help manage this league. Must already be members of the league.'
    )
    sport = models.CharField(max_length=10, choices=[('NFL', 'NFL'), ('NBA', 'NBA')], default='NFL')
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_private = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=True)
    invite_code = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    join_code = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        help_text='Short, shareable code used in the invite link (e.g. CHIEFS24).'
    )

    members = models.ManyToManyField(
        User,
        through='LeagueMembership',
        related_name='leagues'
    )

    def __str__(self):
        return f"{self.name} ({self.sport})"

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if self.join_code:
            self.join_code = self.join_code.strip().upper()
        else:
            self.join_code = self._generate_unique_join_code()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_unique_join_code():
        for _ in range(20):
            code = generate_join_code()
            if not League.objects.filter(join_code=code).exists():
                return code
        # Extremely unlikely fallback: widen the code space.
        return generate_join_code(12)

    def regenerate_join_code(self):
        """Rotate the short invite code (e.g. if the link leaks)."""
        self.join_code = self._generate_unique_join_code()
        self.save(update_fields=['join_code'])
        return self.join_code

    def is_commissioner(self, user):
        """Return True if the user is the primary commissioner or a co-commissioner."""
        if not user or not user.is_authenticated:
            return False
        if user.id == self.commissioner_id:
            return True
        return self.co_commissioners.filter(id=user.id).exists()

    def all_commissioners(self):
        """Return the primary commissioner plus all co-commissioners."""
        return [self.commissioner] + list(self.co_commissioners.all())

    def regenerate_invite_code(self):
        """Rotate the shareable invite code (e.g. if the link leaks)."""
        self.invite_code = uuid.uuid4()
        self.save(update_fields=['invite_code'])
        return self.invite_code

    # Removed the member_count property to avoid conflicts
    # Now use annotation in views: .annotate(member_count=Count('members'))
    
    def get_member_count(self):
        """Use this method when you need member count without annotation"""
        return self.members.count()

    def is_join_locked(self):
        """Return True once the season has started and new members can no
        longer join. Existing members are unaffected — this only gates *new*
        joins/requests (standard pick'em behavior: no entering after kickoff).
        """
        from apps.games.utils import season_has_started
        return season_has_started()

    def get_standings(self):
        """League standings computed live from graded picks.

        Only games that have *concluded* count toward a member's win/loss
        record, so the table updates incrementally as each primetime game
        finishes (e.g. after Thursday night a correct pick immediately shows a
        win, a wrong pick shows a loss, and the still-to-play Sunday/Monday
        games are surfaced as "pending" rather than counted). Tie games are
        recorded as pushes and don't help or hurt the record.
        """
        from apps.picks.models import Pick
        from django.db.models import Sum

        standings = []

        for member in self.members.all():
            picks = Pick.objects.filter(user=member, league=self)

            wins = picks.filter(is_correct=True).count()
            losses = picks.filter(is_correct=False).count()
            # Push: the game finished with no winner, so is_correct stays null.
            pushes = picks.filter(
                is_correct__isnull=True, game__status='final'
            ).count()
            # Pending: a pick whose game hasn't concluded yet (not final/cancelled).
            pending = picks.filter(is_correct__isnull=True).exclude(
                game__status__in=['final', 'cancelled']
            ).count()

            decided = wins + losses
            total_points = picks.filter(is_correct=True).aggregate(
                total=Sum('points')
            )['total'] or 0
            # Accuracy is over decided games only (pushes/pending excluded).
            accuracy = round((wins / decided) * 100, 1) if decided else 0

            record = f"{wins}-{losses}"
            if pushes:
                record = f"{record}-{pushes}"

            standings.append({
                'user': member,
                'wins': wins,
                'losses': losses,
                'pushes': pushes,
                'pending': pending,
                'record': record,
                'accuracy': accuracy,
                'total_points': total_points,
                # Backwards-compatible keys still used by templates/tests:
                'total_predictions': decided,
                'correct_predictions': wins,
            })

        # Rank by points, then accuracy, then most wins, then fewest losses.
        standings.sort(
            key=lambda x: (x['total_points'], x['accuracy'], x['wins'], -x['losses']),
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
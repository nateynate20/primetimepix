# apps/leagues/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from .models import LeagueCreationRequest, LeagueJoinRequest

@receiver(post_save, sender=LeagueCreationRequest)
def notify_creation_request_approved(sender, instance, created, **kwargs):
    if not created and instance.approved:
        send_mail(
            subject="Your league creation request was approved!",
            message=f"Hi {instance.user.username}, your league '{instance.league_name}' has been approved.",
            from_email="no-reply@nflpix.com",
            recipient_list=[instance.user.email],
        )

@receiver(post_save, sender=LeagueJoinRequest)
def notify_join_request_approved(sender, instance, created, **kwargs):
    if not created and instance.approved:
        send_mail(
            subject="Your request to join the league was approved!",
            message=f"Hi {instance.user.username}, your request to join '{instance.league.name}' was approved.",
            from_email="no-reply@nflpix.com",
            recipient_list=[instance.user.email],
        )

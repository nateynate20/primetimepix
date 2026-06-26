from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        # Only create if one doesn't already exist (signup form may have created it)
        Profile.objects.get_or_create(
            user=instance,
            defaults={'team_name': instance.username}
        )
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Ensure every User has exactly one Profile.

    We use `get_or_create` rather than an unconditional `Profile.objects.create`
    so this is safe even if the signal somehow fires more than once for the
    same user (e.g. a `save()` call elsewhere, or a race), and it also means
    running this on a project that already has users (created before this
    app existed) will backfill a Profile for them instead of raising an
    error the next time they're saved.
    """
    Profile.objects.get_or_create(user=instance)

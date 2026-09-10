from django.conf import settings
from django.db import models


def profile_picture_upload_to(instance, filename):
    """
    Build the storage path for an uploaded profile picture.

    We deliberately ignore the original filename beyond its extension
    (never trust user-supplied filenames/paths) and key the file on the
    user's id instead, so re-uploads land in a predictable location and
    nothing from the client controls the path.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    return f"profile_pictures/user_{instance.user_id}.{ext}"


class Profile(models.Model):
    """
    One-to-one extension of Django's built-in User model.

    Kept intentionally small for Phase 3 — just enough for a basic
    social-media profile page. Feed/posts/followers etc. are separate
    concerns for later phases and don't belong on this model.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    profile_picture = models.ImageField(
        upload_to=profile_picture_upload_to,
        blank=True,
        null=True,
    )
    bio = models.CharField(max_length=280, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s profile"

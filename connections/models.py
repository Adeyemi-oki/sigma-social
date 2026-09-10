from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Follow(models.Model):
    """
    Records that `follower` follows `following`.

    related_name choices are picked so a User instance reads naturally:
    `user.following` -- Follow rows for accounts this user follows
    `user.followers` -- Follow rows for accounts that follow this user
    """

    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="following",
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="followers",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]  # newest first
        constraints = [
            # A user can't create more than one Follow row for the
            # same target -- enforced at the database level, not just
            # checked in Python, so it holds even under a race.
            models.UniqueConstraint(fields=["follower", "following"], name="unique_follow_relationship"),
            # A user can't follow themselves -- also enforced at the
            # database level as a backstop to the view-level check.
            models.CheckConstraint(condition=~Q(follower=F("following")), name="prevent_self_follow"),
        ]
        indexes = [
            # Matches the two query shapes this app actually runs:
            # "who does this user follow" and "who follows this user".
            models.Index(fields=["follower"]),
            models.Index(fields=["following"]),
        ]

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"

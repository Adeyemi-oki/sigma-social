from django.conf import settings
from django.db import models
from django.urls import reverse


class Notification(models.Model):
    """
    A single notification for one user about something another user did.

    Deliberately generic (actor + type + optional post/comment) rather
    than one model per event type, so adding a future notification
    type (FOLLOW, MENTION, ...) only means adding a new choice and a
    new "notify_*" helper -- not a new model or a schema change for
    every field it might ever need.
    """

    class NotificationType(models.TextChoices):
        NEW_POST = "NEW_POST", "New post"
        LIKE = "LIKE", "Like"
        COMMENT = "COMMENT", "Comment"
        FOLLOW = "FOLLOW", "Follow"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications_sent",
    )
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices)

    # Optional references to the content the notification is about.
    # Nullable + on_delete=CASCADE: if the post/comment is deleted,
    # the notification about it no longer makes sense either.
    post = models.ForeignKey(
        "posts.Post",
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    comment = models.ForeignKey(
        "posts.Comment",
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]  # newest first
        indexes = [
            # Matches the queries this app actually runs: "this user's
            # unread notifications" and "this user's notifications,
            # newest first".
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["recipient", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.get_notification_type_display()} for {self.recipient.username} from {self.actor.username}"

    def get_action_text(self):
        """
        The notification's text *after* the actor's name, e.g.
        "liked your post." Kept separate from the actor's name so the
        template can link the name to their profile while the rest
        stays plain text inside a single "mark read" button (a link
        can't be nested inside a button in valid HTML).
        """
        if self.notification_type == self.NotificationType.NEW_POST:
            return "posted something new."
        if self.notification_type == self.NotificationType.LIKE:
            return "liked your post."
        if self.notification_type == self.NotificationType.COMMENT:
            return "commented on your post."
        if self.notification_type == self.NotificationType.FOLLOW:
            return "started following you."
        return "did something."

    def get_text(self):
        """Full human-readable sentence, e.g. for the admin or plain-text contexts."""
        return f"{self.actor.username} {self.get_action_text()}"

    def get_absolute_url(self):
        """Where clicking this notification should take the user."""
        if self.notification_type == self.NotificationType.FOLLOW:
            return reverse("profile", kwargs={"username": self.actor.username})
        if self.post_id:
            return reverse("post_detail", kwargs={"pk": self.post_id})
        return reverse("home")

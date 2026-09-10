import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import BooleanField, Count, Exists, OuterRef, Value


def post_image_upload_to(instance, filename):
    """
    Build the storage path for an uploaded post image.

    As with profile pictures, we never trust the client-supplied
    filename beyond its extension -- the path is keyed on the author's
    id plus a random token, so nothing from the upload controls where
    it lands on disk.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    return f"post_images/{instance.author_id}/{uuid.uuid4().hex}.{ext}"


class PostQuerySet(models.QuerySet):
    def with_engagement(self, user):
        """
        Annotate each post with its like count, comment count, and
        (for a logged-in user) whether they've liked it -- all via the
        database, so rendering a feed of many posts never does an
        extra query per post for this information.
        """
        qs = self.annotate(
            like_count=Count("likes", distinct=True),
            comment_count=Count("comments", distinct=True),
        )
        if user.is_authenticated:
            qs = qs.annotate(
                is_liked=Exists(Like.objects.filter(post=OuterRef("pk"), user=user))
            )
        else:
            qs = qs.annotate(is_liked=Value(False, output_field=BooleanField()))
        # Re-assert explicit ordering: annotating with Count() aggregates
        # can otherwise make Django's ORM treat the queryset's ordering
        # as ambiguous, which breaks predictable pagination.
        return qs.order_by("-created_at")


class Post(models.Model):
    """
    A single post in the feed.

    Kept intentionally small for Phase 4 -- text and/or an image,
    authored by exactly one user. Likes/comments are added in Phase 5
    as their own models rather than fields here.
    """

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts",
    )
    content = models.TextField(max_length=2000, blank=True, default="")
    image = models.ImageField(upload_to=post_image_upload_to, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PostQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]  # newest first, everywhere this is queried

    def __str__(self):
        preview = self.content[:30] or "(image only)"
        return f"Post({self.author.username}): {preview}"

    def clean(self):
        """
        Enforce "a post must have content or an image" at the model
        level, so this rule holds regardless of whether the write comes
        from a form, the admin, or a script -- not just the frontend.
        """
        super().clean()
        if not self.content.strip() and not self.image:
            raise ValidationError("A post needs some text or an image.")

    def save(self, *args, **kwargs):
        # Keep stored content trimmed even if clean() wasn't called
        # explicitly (e.g. direct .save() from a script or shell).
        self.content = self.content.strip()
        super().save(*args, **kwargs)


class Like(models.Model):
    """
    Records that a user liked a post.

    The (user, post) uniqueness constraint is enforced at the
    database level -- not just checked in Python -- so it's impossible
    to end up with duplicate likes even under concurrent requests.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="likes",
    )
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "post"], name="unique_like_per_user_per_post"),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} likes Post({self.post_id})"


class Comment(models.Model):
    """A comment left by a user on a post."""

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    content = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]  # oldest first, for a conversational feel

    def __str__(self):
        preview = self.content[:30]
        return f"Comment({self.author.username} on Post {self.post_id}): {preview}"

    def clean(self):
        super().clean()
        if not self.content.strip():
            raise ValidationError("Comment can't be empty.")

    def save(self, *args, **kwargs):
        self.content = self.content.strip()
        super().save(*args, **kwargs)

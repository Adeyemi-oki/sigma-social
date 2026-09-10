"""
Reusable follow-relationship logic.

Kept as plain functions here rather than scattering
`Follow.objects.filter(...)` calls across views/templates, so "is X
following Y" and "how many followers does X have" are each defined
in exactly one place.
"""

from django.contrib.auth import get_user_model

from .models import Follow

User = get_user_model()


def is_following(follower, target):
    """Does `follower` currently follow `target`? False for anonymous users."""
    if not follower.is_authenticated:
        return False
    return Follow.objects.filter(follower=follower, following=target).exists()


def follower_count(user):
    return user.followers.count()


def following_count(user):
    return user.following.count()


def follow_user(follower, target):
    """
    Create a follow relationship if one doesn't already exist.

    Returns (follow, created) like get_or_create -- `created` is False
    if `follower` already followed `target`, which callers use to
    decide whether to fire a notification (only on a genuinely new
    follow, never on a repeat visit to the same follow URL).
    """
    return Follow.objects.get_or_create(follower=follower, following=target)


def unfollow_user(follower, target):
    """
    Remove a follow relationship if one exists.

    A no-op (not an error) if `follower` wasn't following `target` --
    unfollowing something you don't follow simply leaves nothing to do.
    """
    Follow.objects.filter(follower=follower, following=target).delete()


def suggested_users(user, limit=5):
    """
    A simple "People You May Know" list: users this account doesn't
    already follow, excluding the user themself.

    Deliberately not a recommendation algorithm -- no scoring, no
    mutual-follower weighting -- just "people you're not already
    connected to", which is enough for a small friend-group app and
    easy to replace with something smarter later without changing
    any caller.
    """
    if not user.is_authenticated:
        return User.objects.none()

    followed_ids = Follow.objects.filter(follower=user).values_list("following_id", flat=True)
    return (
        User.objects.exclude(pk=user.pk)
        .exclude(pk__in=followed_ids)
        .select_related("profile")
        .order_by("-date_joined")[:limit]
    )

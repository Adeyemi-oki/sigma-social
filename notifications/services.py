"""
Notification creation helpers.

Architecture choice: plain service functions, called explicitly from
the view code at the exact point an action succeeds (a post is saved,
a Like is newly created, a Comment is saved) -- not Django signals.

Why not signals? A `post_save` signal on Like would fire on *every*
save, including the ones our own toggle_like view makes when deleting
a Like (which doesn't emit post_save, but a naive implementation might
still be tempted to use post_delete/post_save together and end up
re-deriving "was this actually a new like?" from inside the signal
handler anyway). Calling `notify_like(like)` directly from the view,
only in the branch where `created` is True, makes "a notification is
created if and only if the action actually happened" obvious by
reading the view -- exactly the "successful creation, not URL visit"
rule this phase asks for -- without hidden signal wiring elsewhere.

Why a function per event type instead of one generic `notify()`?
Each event type needs different recipient logic (new post -> every
other user; like/comment -> just the post's author) and different
self-notification rules. Keeping them separate keeps each function
small and easy to reason about, and adding a future type (FOLLOW,
MENTION, ...) is just a new function here plus a new choice on the
model -- nothing existing has to change.
"""

from django.contrib.auth import get_user_model

from .models import Notification

User = get_user_model()


def notify_new_post(post):
    """
    Notify every other user that `post`'s author posted something new.

    The author never receives a notification about their own post.
    """
    recipients = User.objects.exclude(pk=post.author_id)
    Notification.objects.bulk_create(
        [
            Notification(
                recipient=recipient,
                actor=post.author,
                notification_type=Notification.NotificationType.NEW_POST,
                post=post,
            )
            for recipient in recipients
        ]
    )


def notify_like(like):
    """
    Notify a post's author that `like.user` liked their post.

    Skipped entirely if the user liked their own post -- no
    notification row is created in that case, rather than creating
    one and hiding it, so "self-like" never shows up anywhere,
    including the admin or a future notification count.
    """
    post = like.post
    if like.user_id == post.author_id:
        return

    Notification.objects.create(
        recipient=post.author,
        actor=like.user,
        notification_type=Notification.NotificationType.LIKE,
        post=post,
    )


def notify_comment(comment):
    """
    Notify a post's author that `comment.author` commented on their post.

    Skipped if the user commented on their own post, for the same
    reason as notify_like.
    """
    post = comment.post
    if comment.author_id == post.author_id:
        return

    Notification.objects.create(
        recipient=post.author,
        actor=comment.author,
        notification_type=Notification.NotificationType.COMMENT,
        post=post,
        comment=comment,
    )


def notify_follow(follow):
    """
    Notify a user that someone started following them.

    Callers (see connections/views.py) only invoke this when a Follow
    row was newly created -- not on a repeat visit to the follow URL
    while already following -- so this never needs its own duplicate
    check; one call always means one genuinely new follow event.
    Self-follow is prevented upstream (view + DB constraint), so it's
    never possible to reach this function with actor == recipient.
    """
    Notification.objects.create(
        recipient=follow.following,
        actor=follow.follower,
        notification_type=Notification.NotificationType.FOLLOW,
    )

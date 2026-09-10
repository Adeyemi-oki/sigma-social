from .models import Notification


def unread_notifications_count(request):
    """
    Make `unread_notifications_count` available in every template
    (used by the nav bar), without every view needing to fetch it
    itself.

    Anonymous users have no notifications and no `request.user.id` to
    query against, so we return 0 immediately rather than touching
    the database -- this must never error for a logged-out visitor.
    """
    if not request.user.is_authenticated:
        return {"unread_notifications_count": 0}

    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return {"unread_notifications_count": count}

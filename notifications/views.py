from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def notification_list(request):
    """
    List the current user's notifications, newest-first.

    Filtered by `recipient=request.user` at the query level -- there
    is no way to view anyone else's notifications through this view,
    regardless of what a client might try to pass in.
    """
    notifications = (
        Notification.objects.filter(recipient=request.user)
        .select_related("actor", "actor__profile", "post", "comment")
    )
    return render(request, "notifications/notification_list.html", {"notifications": notifications})


@login_required
@require_POST
def mark_read(request, pk):
    """
    Mark a single notification as read, then go to whatever it's about.

    Ownership is checked server-side: a notification that isn't the
    requesting user's own is rejected with 403, not silently ignored
    or redirected, so changing the ID in the URL can't be used to
    modify (or even reveal the existence/content of) another user's
    notification.
    """
    notification = get_object_or_404(Notification, pk=pk)
    if notification.recipient != request.user:
        return HttpResponseForbidden("You can only manage your own notifications.")

    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])

    return redirect(notification.get_absolute_url())


@login_required
@require_POST
def mark_all_read(request):
    """
    Mark all of the current user's unread notifications as read.

    The update is scoped to `recipient=request.user` at the query
    level, so it can only ever touch this user's own rows no matter
    what.
    """
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return redirect("notifications")

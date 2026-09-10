from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from notifications.services import notify_follow

from .models import Follow
from .services import follow_user, unfollow_user


@login_required
@require_POST
def follow(request, username):
    """
    Follow another user.

    The follower is always `request.user` -- never taken from
    submitted data. The target is looked up by username from the URL.
    Self-following is rejected here (and backed by a database
    constraint), and a repeat follow of someone already followed is a
    harmless no-op rather than an error or a duplicate row.
    """
    target = get_object_or_404(User, username=username)

    if target == request.user:
        messages.error(request, "You can't follow yourself.")
        return redirect("profile", username=username)

    relationship, created = follow_user(request.user, target)
    if created:
        notify_follow(relationship)
        messages.success(request, f"You are now following @{target.username}.")

    return redirect("profile", username=username)


@login_required
@require_POST
def unfollow(request, username):
    """
    Unfollow a user. A no-op if not currently followed -- removing a
    relationship that doesn't exist isn't an error condition.

    Ownership is implicit: the query is always scoped to
    `follower=request.user`, so this can only ever remove the
    requesting user's own follow relationship, never someone else's.
    """
    target = get_object_or_404(User, username=username)
    unfollow_user(request.user, target)
    messages.success(request, f"You unfollowed @{target.username}.")
    return redirect("profile", username=username)


@login_required
def followers_list(request):
    """
    Users who follow the current user.

    Also computes which of them the current user follows back, in a
    single extra query, so the template can show a Follow/Following
    state per row without a query per row.
    """
    followers_qs = (
        request.user.followers.select_related("follower", "follower__profile").order_by("-created_at")
    )
    paginator = Paginator(followers_qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    following_ids = set(
        Follow.objects.filter(follower=request.user).values_list("following_id", flat=True)
    )
    return render(
        request,
        "connections/followers_list.html",
        {"page_obj": page_obj, "following_ids": following_ids},
    )


@login_required
def following_list(request):
    """Users the current user follows."""
    following_qs = (
        request.user.following.select_related("following", "following__profile").order_by("-created_at")
    )
    paginator = Paginator(following_qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "connections/following_list.html", {"page_obj": page_obj})

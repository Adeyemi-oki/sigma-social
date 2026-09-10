from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render

from connections.services import follower_count, following_count, is_following

from .forms import ProfileEditForm


def profile_detail(request, username):
    """
    Public profile page for any user, looked up by username.

    Anyone can view a profile (own or someone else's) -- the template
    decides whether to show the "Edit Profile" button by comparing
    the viewed profile's owner against request.user, and whether to
    show Follow/Following based on the current user's relationship to
    the profile owner.
    """
    profile_user = get_object_or_404(User, username=username)
    # profile_user.profile is guaranteed to exist because of the
    # post_save signal in profiles/signals.py.
    # Only this user's own posts are ever shown here -- the query is
    # explicitly filtered by author, so there's no way posts from
    # other users end up on this page. with_engagement annotates
    # like/comment counts (and whether the viewer has liked each
    # post) without an extra query per post.
    user_posts = profile_user.posts.select_related("author", "author__profile").with_engagement(
        request.user
    )
    return render(
        request,
        "profiles/profile.html",
        {
            "profile_user": profile_user,
            "profile": profile_user.profile,
            "posts": user_posts,
            "follower_count": follower_count(profile_user),
            "following_count": following_count(profile_user),
            "is_following": is_following(request.user, profile_user),
        },
    )


@login_required
def edit_profile(request):
    """
    Lets the logged-in user edit their OWN profile.

    There is no username in this URL and no way to target another
    user's profile through it -- `instance` is always
    `request.user.profile`, so URL manipulation can't be used to
    edit someone else's data.
    """
    profile = request.user.profile

    if request.method == "POST":
        form = ProfileEditForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("profile", username=request.user.username)
    else:
        form = ProfileEditForm(instance=profile)

    return render(request, "profiles/edit_profile.html", {"form": form})

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import CommentForm, PostForm
from .models import Comment, Like, Post
from notifications.services import notify_comment, notify_like, notify_new_post


def _safe_redirect_target(request, fallback_url):
    """
    Redirect back to wherever the like/unlike action was triggered
    from (feed, profile, or post detail) using the HTTP Referer, but
    only if it points at this same site -- never follow an external
    URL supplied by the request, to avoid being used as an open
    redirect.
    """
    referer = request.META.get("HTTP_REFERER")
    if referer and url_has_allowed_host_and_scheme(
        url=referer, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return referer
    return fallback_url


@login_required
def create_post(request):
    """
    Let the logged-in user create a post.

    The author is always `request.user` -- it is never read from the
    submitted form, so there's no way for a client to post as someone
    else no matter what they put in the request.
    """
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            notify_new_post(post)
            messages.success(request, "Post created.")
            return redirect("home")
    else:
        form = PostForm()

    return render(request, "posts/create_post.html", {"form": form})


def post_detail(request, pk):
    """
    Public detail page for a single post: the post itself, its
    engagement (like count / comment count / whether the current
    user has liked it), a paginated list of comments, and a comment
    form for authenticated users.
    """
    post = get_object_or_404(
        Post.objects.select_related("author", "author__profile").with_engagement(request.user),
        pk=pk,
    )
    comments = post.comments.select_related("author", "author__profile")
    paginator = Paginator(comments, 10)  # 10 comments per page
    comments_page = paginator.get_page(request.GET.get("page"))

    context = {
        "post": post,
        "comments_page": comments_page,
        "comment_form": CommentForm(),
    }
    return render(request, "posts/post_detail.html", context)


@login_required
@require_POST
def delete_post(request, pk):
    """
    Delete a post -- POST only, since deletion changes server state.

    Ownership is checked server-side (`post.author == request.user`)
    regardless of whether a delete button was ever shown in the UI;
    a request for a post that isn't the user's own is rejected with
    403, not silently redirected, so URL manipulation can't be used
    to remove someone else's post.
    """
    post = get_object_or_404(Post, pk=pk)
    if post.author != request.user:
        return HttpResponseForbidden("You can only delete your own posts.")

    post.delete()
    messages.success(request, "Post deleted.")
    return redirect("home")


@login_required
@require_POST
def toggle_like(request, pk):
    """
    Like a post if the current user hasn't liked it yet, or unlike it
    if they have -- a single toggle endpoint, as the like/unlike pair
    is really one action from the user's point of view.

    The (user, post) database constraint on Like makes a duplicate
    like impossible even if this were somehow called twice at once;
    here we simply check first so a second click un-likes rather than
    erroring.
    """
    post = get_object_or_404(Post, pk=pk)
    like, created = Like.objects.get_or_create(user=request.user, post=post)
    if created:
        notify_like(like)
    else:
        like.delete()

    return redirect(_safe_redirect_target(request, reverse("post_detail", kwargs={"pk": pk})))


def likes_list(request, pk):
    """Show which users liked a post, each linking to their profile."""
    post = get_object_or_404(Post, pk=pk)
    likers = post.likes.select_related("user", "user__profile").order_by("-created_at")
    return render(request, "posts/likes_list.html", {"post": post, "likers": likers})


@login_required
def add_comment(request, pk):
    """
    Add a comment to a post.

    The post is always the one identified by the URL, and the author
    is always `request.user` -- neither is ever taken from submitted
    form data, so a comment can't be attached to the wrong post or
    credited to the wrong user.
    """
    post = get_object_or_404(Post.objects.with_engagement(request.user), pk=pk)

    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            notify_comment(comment)
            messages.success(request, "Comment added.")
            return redirect("post_detail", pk=post.pk)
    else:
        form = CommentForm()

    # Invalid (or GET) submission: re-render the post detail page with
    # the form's errors attached, rather than losing the user's context.
    comments = post.comments.select_related("author", "author__profile")
    paginator = Paginator(comments, 10)
    comments_page = paginator.get_page(request.GET.get("page"))
    context = {
        "post": post,
        "comments_page": comments_page,
        "comment_form": form,
    }
    return render(request, "posts/post_detail.html", context)


@login_required
@require_POST
def delete_comment(request, pk):
    """
    Delete a comment -- POST only, and only the comment's own author
    may do it. Ownership is checked server-side; a request for
    someone else's comment is rejected with 403 rather than silently
    ignored, so URL manipulation can't be used to remove it.
    """
    comment = get_object_or_404(Comment, pk=pk)
    if comment.author != request.user:
        return HttpResponseForbidden("You can only delete your own comments.")

    post_pk = comment.post_id
    comment.delete()
    messages.success(request, "Comment deleted.")
    return redirect("post_detail", pk=post_pk)

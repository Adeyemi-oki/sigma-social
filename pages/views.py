from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render

from connections.services import suggested_users
from posts.models import Post


def health(request):
    """
    Lightweight health check for Render (or any uptime monitor).

    Deliberately does not touch the database or reveal any internal
    state -- if the WSGI app can respond at all, this is enough signal
    that the process is alive. Public, no auth, plain text.
    """
    return HttpResponse("ok", content_type="text/plain")


def home(request):
    """
    The homepage doubles as the main feed (Phase 4).

    Posts are already ordered newest-first via Post.Meta.ordering, so
    we just paginate that queryset. select_related pulls the author
    and their profile in the same query to avoid an extra query per
    post for the profile picture; with_engagement annotates like/
    comment counts and whether the current user has liked each post,
    all in the database, so displaying a full page of posts never
    costs an extra query per post for this information.
    """
    posts = Post.objects.select_related("author", "author__profile").with_engagement(request.user)
    paginator = Paginator(posts, 10)  # 10 posts per page
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {"page_obj": page_obj}
    if request.user.is_authenticated:
        # Right-rail "Suggested for you" -- reuses the existing Phase 7/8
        # suggestion logic rather than inventing a new backend feature
        # just to fill the sidebar.
        context["rail_suggested_users"] = suggested_users(request.user, limit=4)

    return render(request, "pages/home.html", context)

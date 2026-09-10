from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render

from connections.services import suggested_users
from posts.models import Post

from .services import clean_query, search_posts, search_users

RESULTS_PER_PAGE = 10


@login_required
def search(request):
    """
    Search users and posts for a query string.

    Gated behind login, matching the rest of the site: the search box
    itself only appears in the nav for authenticated users, and this
    keeps the same visibility rules as the feed/notifications/follow
    pages rather than opening a new anonymous-access surface.
    """
    query = clean_query(request.GET.get("q"))
    context = {"query": query}

    if query:
        users_qs = search_users(query)
        posts_qs = search_posts(query, request.user)

        user_paginator = Paginator(users_qs, RESULTS_PER_PAGE)
        user_page_obj = user_paginator.get_page(request.GET.get("upage"))

        post_paginator = Paginator(posts_qs, RESULTS_PER_PAGE)
        post_page_obj = post_paginator.get_page(request.GET.get("page"))

        following_ids = set(request.user.following.values_list("following_id", flat=True))

        context.update(
            {
                "user_page_obj": user_page_obj,
                "post_page_obj": post_page_obj,
                "following_ids": following_ids,
            }
        )

    return render(request, "search/search_results.html", context)


@login_required
def explore(request):
    """
    Simple discovery page: recent posts (newest first, reusing the
    same annotated queryset the feed uses) plus a short "People You
    May Know" list built entirely from the existing Follow system.
    """
    posts_qs = Post.objects.select_related("author", "author__profile").with_engagement(request.user)
    paginator = Paginator(posts_qs, RESULTS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "search/explore.html",
        {
            "page_obj": page_obj,
            "suggested_users": suggested_users(request.user),
            "following_ids": set(),  # suggestions are always not-yet-followed
        },
    )

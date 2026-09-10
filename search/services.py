"""
Search query logic.

Kept as plain functions (not a class-based search engine) since the
underlying queries are just Django ORM filters on existing models --
User and Post. Nothing here duplicates the Follow logic in
`connections`; that app's helpers are imported and reused as-is.
"""

from django.contrib.auth import get_user_model
from django.db.models import Case, IntegerField, Q, Value, When

from posts.models import Post

User = get_user_model()

MAX_QUERY_LENGTH = 100


def clean_query(raw):
    """
    Normalize a raw `?q=` value: strip whitespace and cap length, so a
    huge or all-whitespace string can never reach the database as a
    search term. Never trusts the input further than that -- all
    matching still goes through the Django ORM (icontains), never raw
    SQL.
    """
    return (raw or "").strip()[:MAX_QUERY_LENGTH]


def search_users(query):
    """
    Users whose username, first name, or last name contains `query`
    (case-insensitive), ranked so closer matches come first:
    exact username match, then username starts-with, then everything
    else alphabetically.
    """
    if not query:
        return User.objects.none()

    return (
        User.objects.filter(
            Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query)
        )
        .select_related("profile")
        .annotate(
            match_rank=Case(
                When(username__iexact=query, then=Value(0)),
                When(username__istartswith=query, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )
        )
        .order_by("match_rank", "username")
    )


def search_posts(query, viewer):
    """
    Posts whose content contains `query` (case-insensitive), newest
    first, annotated with the same like/comment engagement data the
    feed uses so results render with zero extra queries per post.
    """
    if not query:
        return Post.objects.none()

    return (
        Post.objects.filter(content__icontains=query)
        .select_related("author", "author__profile")
        .with_engagement(viewer)
    )

"""
URL configuration for the Sigma Social project.

Phase 1: Django admin and a simple homepage.
Phase 2: adds the `users` app (register/login/logout).
Phase 3: adds the `profiles` app (view/edit user profiles).
Phase 4: adds the `posts` app (create/view/delete posts); the
homepage (pages.views.home) now doubles as the main feed.
Phase 6: adds the `notifications` app.
Phase 7: adds the `connections` app (follow/unfollow, followers/
following lists). Its follow/unfollow URLs live under /profile/<username>/
alongside the profiles app's own URLs; Django matches on the full
path, so the two apps' patterns don't collide.
Phase 8: adds the `search` app (search + explore).
Phase 10: adds /health/ for Render's health check.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from pages.views import health, home

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("", home, name="home"),
    path("", include("users.urls")),
    path("", include("posts.urls")),
    path("", include("notifications.urls")),
    path("", include("connections.urls")),
    path("", include("search.urls")),
    path("profile/", include("profiles.urls")),
]

# Serve user-uploaded media files locally during development.
# In production this is handled by the hosting platform / a proper
# storage backend, not by Django itself.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

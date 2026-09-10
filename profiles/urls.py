from django.urls import path

from . import views

urlpatterns = [
    # NOTE: /profile/edit/ must be registered before /profile/<username>/
    # so that "edit" is never swallowed by the <username> pattern.
    path("edit/", views.edit_profile, name="edit_profile"),
    path("<str:username>/", views.profile_detail, name="profile"),
]

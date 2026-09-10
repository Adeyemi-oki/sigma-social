from django.urls import path

from . import views

urlpatterns = [
    path("profile/<str:username>/follow/", views.follow, name="follow_user"),
    path("profile/<str:username>/unfollow/", views.unfollow, name="unfollow_user"),
    path("followers/", views.followers_list, name="followers"),
    path("following/", views.following_list, name="following"),
]

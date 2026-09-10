from django.urls import path

from . import views

urlpatterns = [
    path("create-post/", views.create_post, name="create_post"),
    path("post/<int:pk>/", views.post_detail, name="post_detail"),
    path("post/<int:pk>/delete/", views.delete_post, name="delete_post"),
    path("post/<int:pk>/like/", views.toggle_like, name="toggle_like"),
    path("post/<int:pk>/likes/", views.likes_list, name="post_likes"),
    path("post/<int:pk>/comment/", views.add_comment, name="add_comment"),
    path("comment/<int:pk>/delete/", views.delete_comment, name="delete_comment"),
]

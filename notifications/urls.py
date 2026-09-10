from django.urls import path

from . import views

urlpatterns = [
    path("notifications/", views.notification_list, name="notifications"),
    path("notifications/<int:pk>/read/", views.mark_read, name="mark_notification_read"),
    path("notifications/mark-all-read/", views.mark_all_read, name="mark_all_notifications_read"),
]

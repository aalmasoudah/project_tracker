from django.urls import path

from apps.notifications import views

app_name = "notifications"

urlpatterns = [
    path("", views.notification_list, name="list"),
    path("read-all/", views.mark_all_read, name="read-all"),
    path("preferences/", views.preferences, name="preferences"),
    path("deliveries/", views.delivery_status, name="deliveries"),
    path("<int:notification_id>/open/", views.notification_open, name="open"),
]

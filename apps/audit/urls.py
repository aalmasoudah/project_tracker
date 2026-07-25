"""Read-only audit routes."""

from django.urls import path

from apps.audit import views

app_name = "audit"

urlpatterns = [
    path("", views.event_list, name="list"),
]

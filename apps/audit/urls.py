"""Read-only audit routes."""

from django.urls import path

from apps.audit import views

app_name = "audit"

urlpatterns = [
    path("", views.event_list, name="list"),
    path("export/", views.event_export, name="export"),
    path("<int:event_id>/", views.event_detail, name="detail"),
]

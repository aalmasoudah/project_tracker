from django.urls import path

from apps.operations import views

app_name = "operations"

urlpatterns = [
    path("", views.operations_status, name="status"),
    path("archives/", views.archive_center, name="archives"),
]

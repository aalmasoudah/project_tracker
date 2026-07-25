"""Organization routes."""

from django.urls import path

from apps.organizations import views

app_name = "organizations"

urlpatterns = [
    path("", views.department_list, name="list"),
    path("create/", views.department_create, name="create"),
    path("<int:department_id>/edit/", views.department_update, name="update"),
    path(
        "<int:department_id>/archive/",
        views.department_archive,
        name="archive",
    ),
    path(
        "<int:department_id>/restore/",
        views.department_restore,
        name="restore",
    ),
]

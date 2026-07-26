"""Phase 3 project routes."""

from django.urls import path

from apps.projects import views

app_name = "projects"

urlpatterns = [
    path("", views.project_list, name="list"),
    path("create/", views.project_create, name="create"),
    path("<int:project_id>/", views.project_detail, name="detail"),
    path("<int:project_id>/edit/", views.project_update, name="update"),
    path("<int:project_id>/archive/", views.project_archive, name="archive"),
    path("<int:project_id>/restore/", views.project_restore, name="restore"),
    path("<int:project_id>/team/", views.project_team, name="team"),
    path("<int:project_id>/history/", views.project_history, name="history"),
    path("clients/", views.client_list, name="client_list"),
    path("clients/create/", views.client_create, name="client_create"),
    path("clients/<int:record_id>/edit/", views.client_update, name="client_update"),
    path(
        "clients/<int:record_id>/archive/",
        views.client_archive,
        name="client_archive",
    ),
    path(
        "clients/<int:record_id>/restore/",
        views.client_restore,
        name="client_restore",
    ),
    path("categories/", views.category_list, name="category_list"),
    path("categories/create/", views.category_create, name="category_create"),
    path(
        "categories/<int:record_id>/edit/",
        views.category_update,
        name="category_update",
    ),
    path(
        "categories/<int:record_id>/archive/",
        views.category_archive,
        name="category_archive",
    ),
    path(
        "categories/<int:record_id>/restore/",
        views.category_restore,
        name="category_restore",
    ),
]

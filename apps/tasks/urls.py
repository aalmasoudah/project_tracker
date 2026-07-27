"""Phase 5 task routes."""

from django.urls import path

from apps.tasks import views

app_name = "tasks"

urlpatterns = [
    path("", views.task_list, name="list"),
    path("create/", views.task_create, name="create"),
    path("<int:task_id>/", views.task_detail, name="detail"),
    path("<int:task_id>/edit/", views.task_update, name="update"),
    path(
        "<int:task_id>/my-update/", views.assigned_task_update, name="assigned_update"
    ),
    path("<int:task_id>/assignments/", views.task_assignments, name="assignments"),
    path("<int:task_id>/comment/", views.task_comment, name="comment"),
    path("<int:task_id>/tags/", views.task_tags, name="tags"),
    path("<int:task_id>/files/", views.task_file_upload, name="file_upload"),
    path("<int:task_id>/archive/", views.task_archive, name="archive"),
    path("<int:task_id>/restore/", views.task_restore, name="restore"),
    path("<int:task_id>/history/", views.task_history, name="history"),
    path(
        "files/<int:file_id>/download/", views.task_file_download, name="file_download"
    ),
    path("tags/", views.tag_list, name="tag_list"),
    path("tags/create/", views.tag_create, name="tag_create"),
    path("tags/<int:tag_id>/edit/", views.tag_update, name="tag_update"),
    path("tags/<int:tag_id>/archive/", views.tag_archive, name="tag_archive"),
    path("tags/<int:tag_id>/restore/", views.tag_restore, name="tag_restore"),
]

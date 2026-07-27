"""Phase 4 course and trainer routes."""

from django.urls import path

from apps.courses import views

app_name = "courses"

urlpatterns = [
    path("", views.course_list, name="list"),
    path("create/", views.course_create, name="create"),
    path("<int:course_id>/", views.course_detail, name="detail"),
    path("<int:course_id>/edit/", views.course_update, name="update"),
    path("<int:course_id>/archive/", views.course_archive, name="archive"),
    path("<int:course_id>/restore/", views.course_restore, name="restore"),
    path("<int:course_id>/trainers/", views.course_trainers, name="trainers"),
    path("<int:course_id>/files/", views.course_file_upload, name="file_upload"),
    path("<int:course_id>/history/", views.course_history, name="history"),
    path(
        "files/<int:file_id>/download/",
        views.course_file_download,
        name="file_download",
    ),
    path("trainers/", views.trainer_list, name="trainer_list"),
    path("trainers/create/", views.trainer_create, name="trainer_create"),
    path("trainers/<int:trainer_id>/", views.trainer_detail, name="trainer_detail"),
    path(
        "trainers/<int:trainer_id>/edit/", views.trainer_update, name="trainer_update"
    ),
    path(
        "trainers/<int:trainer_id>/archive/",
        views.trainer_archive,
        name="trainer_archive",
    ),
    path(
        "trainers/<int:trainer_id>/restore/",
        views.trainer_restore,
        name="trainer_restore",
    ),
]

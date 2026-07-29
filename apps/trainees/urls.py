from django.urls import path

from apps.trainees import views

app_name = "trainees"

urlpatterns = [
    path("", views.enrollment_list, name="list"),
    path("new/", views.enrollment_create, name="create"),
    path("<int:enrollment_id>/", views.enrollment_detail, name="detail"),
    path("<int:enrollment_id>/edit/", views.enrollment_update, name="update"),
    path("<int:enrollment_id>/archive/", views.enrollment_archive, name="archive"),
    path("<int:enrollment_id>/restore/", views.enrollment_restore, name="restore"),
    path("imports/", views.import_history, name="import-history"),
    path("imports/upload/", views.import_upload, name="import-upload"),
    path("imports/sample.csv", views.sample_csv, name="sample-csv"),
    path("imports/<int:batch_id>/", views.import_preview, name="import-preview"),
    path(
        "imports/<int:batch_id>/cancel/",
        views.import_cancel,
        name="import-cancel",
    ),
]

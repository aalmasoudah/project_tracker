from django.urls import path

from apps.approvals import views

app_name = "approvals"

urlpatterns = [
    path("milestones/", views.milestone_list, name="milestone_list"),
    path("milestones/create/", views.milestone_create, name="milestone_create"),
    path(
        "milestones/<int:milestone_id>/",
        views.milestone_detail,
        name="milestone_detail",
    ),
    path(
        "milestones/<int:milestone_id>/edit/",
        views.milestone_update,
        name="milestone_update",
    ),
    path(
        "milestones/<int:milestone_id>/archive/",
        views.milestone_archive,
        name="milestone_archive",
    ),
    path(
        "milestones/<int:milestone_id>/restore/",
        views.milestone_restore,
        name="milestone_restore",
    ),
    path("requests/", views.approval_queue, name="queue"),
    path("requests/<int:request_id>/", views.approval_detail, name="detail"),
    path(
        "requests/<int:request_id>/approve/",
        views.approval_approve,
        name="approve",
    ),
    path(
        "requests/<int:request_id>/reject/",
        views.approval_reject,
        name="reject",
    ),
    path(
        "submit/<str:target_type>/<int:target_id>/",
        views.approval_submit,
        name="submit",
    ),
]

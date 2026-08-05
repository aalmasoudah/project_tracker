from django.urls import path

from apps.project_agents import views

app_name = "project_agents"

urlpatterns = [
    path("projects/<int:project_id>/new/", views.agent_request, name="request"),
    path("runs/<uuid:run_id>/", views.agent_detail, name="detail"),
    path("runs/<uuid:run_id>/status/", views.agent_status, name="status"),
    path("runs/<uuid:run_id>/review/", views.agent_review, name="review"),
    path("runs/<uuid:run_id>/cancel/", views.agent_cancel, name="cancel"),
    path(
        "proposals/<uuid:proposal_id>/approve/", views.proposal_approve, name="approve"
    ),
    path("proposals/<uuid:proposal_id>/reject/", views.proposal_reject, name="reject"),
]

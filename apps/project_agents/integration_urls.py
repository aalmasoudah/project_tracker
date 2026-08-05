from django.urls import path

from apps.project_agents import integration_views

app_name = "project_agent_integration"

urlpatterns = [
    path("events/claim/", integration_views.claim_event, name="claim"),
    path("events/callback/", integration_views.callback, name="callback"),
]

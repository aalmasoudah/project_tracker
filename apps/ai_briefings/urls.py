from django.urls import path

from apps.ai_briefings import views

app_name = "ai_briefings"

urlpatterns = [
    path(
        "projects/<int:project_id>/new/",
        views.briefing_request,
        name="request",
    ),
    path("<int:briefing_id>/", views.briefing_detail, name="detail"),
    path("<int:briefing_id>/status/", views.briefing_status, name="status"),
    path("<int:briefing_id>/review/", views.briefing_review, name="review"),
]

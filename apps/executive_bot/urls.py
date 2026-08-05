from django.urls import path

from apps.executive_bot import views

app_name = "executive_bot"

urlpatterns = [
    path("reports/start/", views.start_report, name="start_report"),
    path("reports/status/", views.report_status, name="report_status"),
    path("reports/<uuid:report_id>/download/", views.download_report, name="download"),
    path("alerts/claim/", views.claim_alerts, name="claim_alerts"),
    path("alerts/acknowledge/", views.acknowledge_alerts, name="acknowledge_alerts"),
]

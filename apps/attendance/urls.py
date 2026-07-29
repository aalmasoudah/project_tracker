from django.urls import path

from apps.attendance import views

app_name = "attendance"

urlpatterns = [
    path("", views.session_list, name="list"),
    path("new/", views.session_create, name="create"),
    path("<int:session_id>/", views.session_detail, name="detail"),
    path("<int:session_id>/archive/", views.session_archive, name="archive"),
    path("<int:session_id>/link/", views.link_issue, name="link-issue"),
    path("t/<str:token>/", views.trainer_attendance, name="trainer"),
]

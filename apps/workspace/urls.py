from django.urls import path

from apps.workspace import views

app_name = "workspace"

urlpatterns = [
    path("search/", views.search, name="search"),
    path("filters/", views.saved_filter_list, name="filters"),
    path("filters/save/", views.saved_filter_create, name="filter_save"),
    path("filters/<int:filter_id>/use/", views.saved_filter_use, name="filter_use"),
    path(
        "filters/<int:filter_id>/delete/",
        views.saved_filter_delete,
        name="filter_delete",
    ),
    path("kanban/", views.kanban, name="kanban"),
    path("calendar/", views.calendar, name="calendar"),
    path("timeline/", views.timeline, name="timeline"),
    path("gantt/", views.gantt, name="gantt"),
]

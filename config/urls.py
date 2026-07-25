"""URL configuration for the engineering foundation."""

from django.contrib import admin
from django.urls import include, path

from config import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("health/", views.health, name="health"),
    path("", views.home, name="home"),
]

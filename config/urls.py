"""URL configuration for the engineering foundation."""

from django.contrib import admin
from django.urls import include, path

from apps.accounts import views as account_views
from config import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "i18n/setlang/",
        account_views.set_language_preference,
        name="set_language",
    ),
    path("accounts/", include("apps.accounts.urls")),
    path("departments/", include("apps.organizations.urls")),
    path("audit/", include("apps.audit.urls")),
    path("health/", views.health, name="health"),
    path("", views.home, name="home"),
]

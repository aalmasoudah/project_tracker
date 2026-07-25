"""Account and authentication routes."""

from django.urls import path

from apps.accounts import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.TrackerLoginView.as_view(), name="login"),
    path("logout/", views.TrackerLogoutView.as_view(), name="logout"),
    path("password/change/", views.password_change, name="password_change"),
    path("me/", views.profile, name="profile"),
    path("users/", views.account_list, name="list"),
    path("users/create/", views.account_create, name="create"),
    path("users/<int:user_id>/", views.account_detail, name="detail"),
    path("users/<int:user_id>/edit/", views.account_update, name="update"),
    path(
        "users/<int:user_id>/deactivate/",
        views.account_deactivate,
        name="deactivate",
    ),
    path(
        "users/<int:user_id>/reactivate/",
        views.account_reactivate,
        name="reactivate",
    ),
    path(
        "users/<int:user_id>/password/reset/",
        views.account_password_reset,
        name="password_reset",
    ),
]

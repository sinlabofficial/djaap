from django.urls import path

from . import auth_views, views

app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard_home, name="home"),
    path("profile/", views.profile, name="profile"),
    path("settings/", views.settings, name="settings"),
    path("logs/", views.logs, name="logs"),
    path(
        "logs/webhooks/<uuid:event_id>/replay/",
        views.webhook_replay,
        name="webhook_replay",
    ),
    path("login/", auth_views.session_login, name="login"),
    path("auth/logout/", auth_views.session_logout, name="logout"),
    path("auth/check/", auth_views.check_session, name="check_session"),
    path("users/", views.user_list, name="user_list"),
    path("users/table/", views.users_table, name="users_table"),
    path("users/export/", views.user_export, name="user_export"),
    path("users/import/", views.user_import, name="user_import"),
    path("users/import-template/", views.user_import_template, name="user_import_template"),
    path("users/panel/empty/", views.user_panel_empty, name="user_panel_empty"),
    path("users/create/", views.user_create, name="user_create"),
    path("users/<uuid:user_id>/edit/", views.user_edit, name="user_edit"),
    path("users/<uuid:user_id>/delete/", views.user_delete, name="user_delete"),
    path(
        "users/<uuid:user_id>/roles/assign/",
        views.user_assign_role,
        name="user_assign_role",
    ),
    path(
        "users/<uuid:user_id>/roles/<uuid:role_id>/remove/",
        views.user_remove_role,
        name="user_remove_role",
    ),
    path("roles/", views.role_list, name="role_list"),
    path("roles/table/", views.roles_table, name="roles_table"),
    path("roles/create/", views.role_create, name="role_create"),
    path("roles/<uuid:role_id>/edit/", views.role_edit, name="role_edit"),
    path("roles/<uuid:role_id>/delete/", views.role_delete, name="role_delete"),
    path("roles/<uuid:role_id>/", views.role_detail, name="role_detail"),
    path(
        "roles/<uuid:role_id>/permissions/assign/",
        views.role_permission_assign,
        name="role_permission_assign",
    ),
    path(
        "roles/<uuid:role_id>/permissions/<uuid:permission_id>/remove/",
        views.role_permission_remove,
        name="role_permission_remove",
    ),
    path("permissions/", views.permission_list, name="permission_list"),
    path("permissions/create/", views.permission_create, name="permission_create"),
    path(
        "permissions/<uuid:permission_id>/edit/",
        views.permission_edit,
        name="permission_edit",
    ),
    path(
        "permissions/<uuid:permission_id>/delete/",
        views.permission_delete,
        name="permission_delete",
    ),
]

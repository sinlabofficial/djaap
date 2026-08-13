from typing import Any, cast
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.core.models import User
from apps.core.selectors import (
    organization_settings_get,
    user_has_permission,
    user_profile_get,
)
from apps.core.services import (
    assign_permission_to_role,
    assign_role_to_user,
    organization_presentation_policy_update,
    organization_settings_update,
    remove_permission_from_role,
    remove_role_from_user,
    user_presentation_preference_update,
    user_update_profile,
)
from apps.core.services import (
    permission_create as permission_create_service,
)
from apps.core.services import (
    permission_delete as permission_delete_service,
)
from apps.core.services import (
    permission_update as permission_update_service,
)
from apps.core.services import (
    role_create as role_create_service,
)
from apps.core.services import (
    role_delete as role_delete_service,
)
from apps.core.services import (
    role_update as role_update_service,
)
from apps.core.services import user_create as user_create_service
from apps.core.services import user_update as user_update_service
from apps.core.user_import_export import (
    IMPORT_HEADERS,
    csv_bytes,
    import_users,
    user_export_rows,
    xls_bytes,
)
from apps.platform_runtime.selectors import webhook_event_get
from apps.platform_runtime.webhooks import replay_webhook_event

from .forms import (
    DashboardUserForm,
    LogFilterForm,
    OrganizationSettingsForm,
    PermissionForm,
    RealtimeLogFilterForm,
    RoleForm,
    RuntimeLogFilterForm,
    UserImportForm,
    UserProfileForm,
    UserRoleAssignForm,
    WebhookLogFilterForm,
)
from .selectors import (
    LOG_TABS,
    dashboard_log_entries,
    dashboard_permissions_list,
    dashboard_realtime_log_entries,
    dashboard_role_detail_get,
    dashboard_roles_list,
    dashboard_runtime_log_entries,
    dashboard_runtime_summary_get,
    dashboard_summary_get,
    dashboard_users_list,
    dashboard_webhook_log_entries,
)


def staff_required(view_func):
    return user_passes_test(
        lambda user: user.is_authenticated and (user.is_staff or user.is_superuser),
        login_url="/dashboard/login/",
    )(view_func)


def permission_required(resource: str, action: str, *, allow_staff: bool = True):
    def decorator(view_func):
        return user_passes_test(
            lambda user: (
                user.is_authenticated
                and (
                    user.is_superuser
                    or (allow_staff and user.is_staff)
                    or user_has_permission(user=user, permission=f"{resource}:{action}")
                )
            ),
            login_url="/dashboard/login/",
        )(view_func)

    return decorator


def is_htmx(request: HttpRequest) -> bool:
    return request.headers.get("HX-Request") == "true"


def htmx_trigger(status: int = 204, event: str = "usersChanged") -> HttpResponse:
    response = HttpResponse(status=status)
    response["HX-Trigger"] = event
    return response


def filtered_users(request: HttpRequest):
    return dashboard_users_list(
        email=request.GET.get("email", "").strip(),
        is_staff=request.GET.get("is_staff", ""),
        is_active=request.GET.get("is_active", ""),
        role_id=request.GET.get("role", "").strip(),
    )


def users_table_context(request: HttpRequest) -> dict:
    paginator = Paginator(filtered_users(request), 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    query = request.GET.copy()
    query.pop("page", None)

    return {
        "page_obj": page_obj,
        "querystring": urlencode(query, doseq=True),
        "roles": dashboard_roles_list(),
        "filters": {
            "email": request.GET.get("email", ""),
            "is_staff": request.GET.get("is_staff", ""),
            "is_active": request.GET.get("is_active", ""),
            "role": request.GET.get("role", ""),
        },
    }


@login_required(login_url="/dashboard/login/")
def dashboard_home(request: HttpRequest) -> HttpResponse:
    context = dashboard_summary_get()
    runtime_summary_visible = request.user.is_superuser or user_has_permission(
        user=cast(User, request.user), permission="runtime_logs:view"
    )
    context["runtime_summary_visible"] = runtime_summary_visible
    if runtime_summary_visible:
        context.update(dashboard_runtime_summary_get())
    return render(request, "pages/dashboard_home.html", context)


@login_required(login_url="/dashboard/login/")
def profile(request: HttpRequest) -> HttpResponse:
    user = user_profile_get(user=request.user)
    if user is None:
        raise Http404("Profile not found.")

    form = UserProfileForm(request.POST or None, request.FILES or None, instance=user)
    if request.method == "POST" and form.is_valid():
        new_password = form.cleaned_data.get("new_password") or None
        user_update_profile(
            user=user,
            profile_name=form.cleaned_data["profile_name"],
            profile_photo=form.cleaned_data.get("profile_photo"),
            password=new_password,
        )
        user_presentation_preference_update(
            user=user,
            presentation_mode=form.cleaned_data.get("presentation_mode")
            or user.presentation_mode,
        )
        form = UserProfileForm(instance=user)
        return render(request, "pages/profile.html", {"form": form, "saved": True})

    return render(request, "pages/profile.html", {"form": form})


@staff_required
def settings(request: HttpRequest) -> HttpResponse:
    organization = organization_settings_get()
    form = OrganizationSettingsForm(
        request.POST or None,
        request.FILES or None,
        instance=organization,
    )

    active_tab = (
        request.POST.get("tab") if request.method == "POST" else request.GET.get("tab")
    )
    active_tab = (
        active_tab
        if active_tab in {"basic", "users", "roles", "authentication"}
        else "basic"
    )
    saved = False
    tab_context = {}

    if active_tab == "users":
        tab_context.update(users_table_context(request))
        tab_context["user_import_form"] = UserImportForm()
    elif active_tab == "roles":
        tab_context.update(roles_context(request))

    if request.method == "POST" and form.is_valid():
        organization = organization_settings_update(
            actor=request.user,
            organization_name=form.cleaned_data["organization_name"],
            logo=form.cleaned_data.get("logo"),
            description=form.cleaned_data.get("description", ""),
            address=form.cleaned_data.get("address", ""),
            phone=form.cleaned_data.get("phone", ""),
            email=form.cleaned_data.get("email", ""),
        )
        organization = organization_presentation_policy_update(
            actor=cast(User, request.user),
            presentation_mode=cast(
                str,
                form.cleaned_data.get("presentation_mode")
                or getattr(organization, "presentation_mode", "default"),
            ),
            mobile_presentation_enabled=form.cleaned_data.get(
                "mobile_presentation_enabled", False
            ),
        )
        form = OrganizationSettingsForm(instance=organization)
        saved = True

    return render(
        request,
        "pages/settings.html",
        {
            "form": form,
            "organization": organization,
            "active_tab": active_tab,
            "saved": saved,
            "settings_tabs": [
                ("basic", "Basic information", "building-2"),
                ("users", "User", "users"),
                ("roles", "Roles", "shield-check"),
                ("authentication", "Authentication", "key-round"),
            ],
            **tab_context,
        },
    )


@permission_required("runtime_logs", "view", allow_staff=False)
def logs(request: HttpRequest) -> HttpResponse:
    active_tab = request.GET.get("tab", "access")
    if active_tab not in {"access", "background_jobs", "webhooks", "realtime"}:
        active_tab = "access"

    context: dict[str, Any] = {
        "active_tab": active_tab,
        "log_tabs": [(key, value["label"]) for key, value in LOG_TABS.items()],
    }
    if active_tab == "background_jobs":
        runtime_log_filter_form = RuntimeLogFilterForm(request.GET or None)
        filters: dict[str, Any] = {}
        if runtime_log_filter_form.is_valid():
            filters = dict(runtime_log_filter_form.cleaned_data)
        runtime_logs = dashboard_runtime_log_entries(
            status=filters.get("status", ""),
            event_type=filters.get("event_type", ""),
            severity=filters.get("severity", ""),
            correlation_id=filters.get("correlation_id", ""),
            date_from=filters.get("date_from"),
            date_to=filters.get("date_to"),
        )
        runtime_page_obj = Paginator(runtime_logs, 20).get_page(request.GET.get("page"))
        query = request.GET.copy()
        query.pop("page", None)
        context.update(
            {
                "runtime_log_filter_form": runtime_log_filter_form,
                "runtime_page_obj": runtime_page_obj,
                "runtime_querystring": urlencode(query, doseq=True),
            }
        )
    elif active_tab == "webhooks":
        webhook_filter_form = WebhookLogFilterForm(request.GET or None)
        filters = dict(webhook_filter_form.cleaned_data) if webhook_filter_form.is_valid() else {}
        webhook_logs = dashboard_webhook_log_entries(**filters)
        webhook_page_obj = Paginator(webhook_logs, 20).get_page(request.GET.get("page"))
        query = request.GET.copy()
        query.pop("page", None)
        context.update(
            {
                "webhook_log_filter_form": webhook_filter_form,
                "webhook_page_obj": webhook_page_obj,
                "webhook_querystring": urlencode(query, doseq=True),
                "can_replay": request.user.is_superuser
                or user_has_permission(
                    user=cast(User, request.user), permission="runtime_logs:replay"
                ),
            }
        )
    elif active_tab == "realtime":
        realtime_filter_form = RealtimeLogFilterForm(request.GET or None)
        filters = dict(realtime_filter_form.cleaned_data) if realtime_filter_form.is_valid() else {}
        realtime_logs = dashboard_realtime_log_entries(**filters)
        realtime_page_obj = Paginator(realtime_logs, 20).get_page(request.GET.get("page"))
        query = request.GET.copy()
        query.pop("page", None)
        context.update(
            {
                "realtime_log_filter_form": realtime_filter_form,
                "realtime_page_obj": realtime_page_obj,
                "realtime_querystring": urlencode(query, doseq=True),
            }
        )
    else:
        log_filter_form = LogFilterForm(request.GET or None)
        access_filters: dict[str, Any] = {}
        if log_filter_form.is_valid():
            access_filters = dict(log_filter_form.cleaned_data)
        context.update(
            {
                "log_filter_form": log_filter_form,
                "log_entries": dashboard_log_entries(
                    tab=active_tab,
                    status=access_filters.get("status", ""),
                    action=access_filters.get("type", ""),
                    date_from=access_filters.get("date_from"),
                    date_to=access_filters.get("date_to"),
                ),
            }
        )
    return render(
        request,
        "pages/logs.html",
        context,
    )


@permission_required("runtime_logs", "replay", allow_staff=False)
@require_POST
def webhook_replay(request: HttpRequest, event_id) -> HttpResponse:
    event = webhook_event_get(event_id=event_id)
    if event is None:
        raise Http404("Webhook event not found.")
    try:
        replay_webhook_event(event=event, actor=request.user)
    except ValueError as error:
        raise Http404(str(error)) from error
    return HttpResponseRedirect("/dashboard/logs/?tab=webhooks")


@login_required(login_url="/dashboard/login/")
def user_list(request: HttpRequest) -> HttpResponse:
    context = users_table_context(request)
    return render(request, "pages/users.html", context)


@permission_required("users", "manage")
def users_table(request: HttpRequest) -> HttpResponse:
    return render(request, "pages/users_table.html", users_table_context(request))


@staff_required
@permission_required("users", "manage", allow_staff=False)
def user_export(request: HttpRequest) -> HttpResponse:
    rows = user_export_rows(dashboard_users_list())
    file_format = request.GET.get("format", "csv").lower()
    if file_format == "xls":
        response = HttpResponse(xls_bytes(rows), content_type="application/vnd.ms-excel")
        response["Content-Disposition"] = 'attachment; filename="users.xls"'
        return response
    response = HttpResponse(csv_bytes(rows), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="users.csv"'
    return response


@staff_required
@permission_required("users", "manage", allow_staff=False)
def user_import_template(request: HttpRequest) -> HttpResponse:
    rows = [list(IMPORT_HEADERS)]
    rows.append(["user@example.com", "", "", "Example User", "false", "true", "ChangeMe123"])
    file_format = request.GET.get("format", "xls").lower()
    if file_format == "csv":
        response = HttpResponse(csv_bytes(rows), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="user-import-template.csv"'
        return response
    response = HttpResponse(xls_bytes(rows), content_type="application/vnd.ms-excel")
    response["Content-Disposition"] = 'attachment; filename="user-import-template.xls"'
    return response


@staff_required
@permission_required("users", "manage", allow_staff=False)
@require_POST
def user_import(request: HttpRequest) -> HttpResponse:
    form = UserImportForm(request.POST, request.FILES)
    if form.is_valid():
        try:
            result = import_users(upload=form.cleaned_data["file"])
        except ValueError as error:
            form.add_error("file", str(error))
        else:
            response = HttpResponseRedirect("/dashboard/settings/?tab=users")
            response["HX-Trigger"] = "usersChanged"
            response["X-Import-Created"] = str(result.created)
            response["X-Import-Updated"] = str(result.updated)
            return response
    context = users_table_context(request)
    context["user_import_form"] = form
    context["active_tab"] = "users"
    return render(request, "pages/settings.html", {
        "form": OrganizationSettingsForm(instance=organization_settings_get()),
        "organization": organization_settings_get(),
        "active_tab": "users",
        "saved": False,
        "settings_tabs": [
            ("basic", "Basic information", "building-2"),
            ("users", "User", "users"),
            ("roles", "Roles", "shield-check"),
            ("authentication", "Authentication", "key-round"),
        ],
        **context,
    })


@permission_required("users", "manage")
def user_panel_empty(request: HttpRequest) -> HttpResponse:
    return render(request, "pages/user_panel_empty.html")


@permission_required("users", "manage")
def user_create(request: HttpRequest) -> HttpResponse:
    form = DashboardUserForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user_create_service(**_dashboard_user_data(form))
        response = render(
            request,
            "pages/user_form.html",
            {"form": DashboardUserForm(), "mode": "create"},
        )
        response["HX-Trigger"] = "usersChanged"
        return response

    return render(request, "pages/user_form.html", {"form": form, "mode": "create"})


@permission_required("users", "manage")
def user_edit(request: HttpRequest, user_id) -> HttpResponse:
    user = dashboard_users_list().filter(id=user_id).first()
    if user is None:
        raise Http404("User not found.")
    form = DashboardUserForm(request.POST or None, instance=user)
    if request.method == "POST" and form.is_valid():
        user_update_service(user=user, **_dashboard_user_data(form))
        response = render(
            request,
            "pages/user_form.html",
            {"form": form, "mode": "edit", "user_obj": user, "saved": True},
        )
        response["HX-Trigger"] = "usersChanged"
        return response

    return render(
        request,
        "pages/user_form.html",
        {"form": form, "mode": "edit", "user_obj": user},
    )


@permission_required("users", "manage")
@require_POST
def user_delete(request: HttpRequest, user_id) -> HttpResponse:
    user = dashboard_users_list().filter(id=user_id).first()
    if user is None:
        raise Http404("User not found.")
    user.delete()
    return htmx_trigger()


@permission_required("roles", "assign")
@require_POST
def user_assign_role(request: HttpRequest, user_id) -> HttpResponse:
    user = dashboard_users_list().filter(id=user_id).first()
    if user is None:
        raise Http404("User not found.")
    form = UserRoleAssignForm(request.POST, user=user)
    if form.is_valid():
        assign_role_to_user(
            user=user, role=form.cleaned_data["role"], assigned_by=request.user
        )
    return htmx_trigger()


@permission_required("roles", "assign")
@require_POST
def user_remove_role(request: HttpRequest, user_id, role_id) -> HttpResponse:
    user = dashboard_users_list().filter(id=user_id).first()
    if user is None:
        raise Http404("User not found.")
    role = dashboard_roles_list().filter(id=role_id).first()
    if role is None:
        raise Http404("Role not found.")
    remove_role_from_user(user=user, role=role)
    return htmx_trigger()


@login_required(login_url="/dashboard/login/")
def role_list(request: HttpRequest) -> HttpResponse:
    return render(request, "pages/roles.html", roles_context(request))


@login_required(login_url="/dashboard/login/")
def roles_table(request: HttpRequest) -> HttpResponse:
    return render(request, "pages/roles_table.html", roles_context(request))


@login_required(login_url="/dashboard/login/")
def role_detail(request: HttpRequest, role_id) -> HttpResponse:
    role_data = dashboard_role_detail_get(role_id=role_id)
    if role_data is None:
        raise Http404("Role not found.")
    role, user_count = role_data
    return render(
        request,
        "pages/role_detail.html",
        {
            "role": role,
            "user_count": user_count,
            "permissions": dashboard_permissions_list(),
        },
    )


def roles_context(request: HttpRequest) -> dict:
    queryset = dashboard_roles_list().prefetch_related("permissions")
    paginator = Paginator(queryset, 20)
    return {"page_obj": paginator.get_page(request.GET.get("page"))}


@permission_required("roles", "manage")
def role_create(request: HttpRequest) -> HttpResponse:
    form = RoleForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        role_create_service(**form.cleaned_data)
        response = render(
            request, "pages/role_form.html", {"form": RoleForm(), "saved": True}
        )
        response["HX-Trigger"] = "rolesChanged"
        return response
    return render(request, "pages/role_form.html", {"form": form})


@permission_required("roles", "manage")
def role_edit(request: HttpRequest, role_id) -> HttpResponse:
    role_data = dashboard_role_detail_get(role_id=role_id)
    if role_data is None:
        raise Http404("Role not found.")
    role, _ = role_data
    form = RoleForm(request.POST or None, instance=role)
    if request.method == "POST" and form.is_valid():
        role_update_service(role=role, **form.cleaned_data)
        response = render(
            request,
            "pages/role_form.html",
            {"form": RoleForm(instance=role), "saved": True, "role": role},
        )
        response["HX-Trigger"] = "rolesChanged"
        return response
    return render(request, "pages/role_form.html", {"form": form, "role": role})


@permission_required("roles", "manage")
@require_POST
def role_delete(request: HttpRequest, role_id) -> HttpResponse:
    role_data = dashboard_role_detail_get(role_id=role_id)
    if role_data is None:
        raise Http404("Role not found.")
    role_delete_service(role=role_data[0])
    return htmx_trigger(event="rolesChanged")


@permission_required("roles", "manage")
@require_POST
def role_permission_assign(request: HttpRequest, role_id) -> HttpResponse:
    role_data = dashboard_role_detail_get(role_id=role_id)
    permission = (
        dashboard_permissions_list().filter(id=request.POST.get("permission")).first()
    )
    if role_data is None or permission is None:
        raise Http404("Role or permission not found.")
    assign_permission_to_role(role=role_data[0], permission=permission)
    return htmx_trigger(event="rolesChanged")


@permission_required("roles", "manage")
@require_POST
def role_permission_remove(
    request: HttpRequest, role_id, permission_id
) -> HttpResponse:
    role_data = dashboard_role_detail_get(role_id=role_id)
    permission = dashboard_permissions_list().filter(id=permission_id).first()
    if role_data is None or permission is None:
        raise Http404("Role or permission not found.")
    remove_permission_from_role(role=role_data[0], permission=permission)
    return htmx_trigger(event="rolesChanged")


@login_required(login_url="/dashboard/login/")
def permission_list(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "pages/permissions.html",
        {"permissions": dashboard_permissions_list()},
    )


@permission_required("roles", "manage")
def permission_create(request: HttpRequest) -> HttpResponse:
    form = PermissionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        permission_create_service(**form.cleaned_data)
        response = render(
            request,
            "pages/permission_form.html",
            {"form": PermissionForm(), "saved": True},
        )
        response["HX-Trigger"] = "rolesChanged"
        return response
    return render(request, "pages/permission_form.html", {"form": form})


@permission_required("roles", "manage")
def permission_edit(request: HttpRequest, permission_id) -> HttpResponse:
    permission = dashboard_permissions_list().filter(id=permission_id).first()
    if permission is None:
        raise Http404("Permission not found.")
    form = PermissionForm(request.POST or None, instance=permission)
    if request.method == "POST" and form.is_valid():
        permission_update_service(permission=permission, **form.cleaned_data)
        response = render(
            request,
            "pages/permission_form.html",
            {
                "form": PermissionForm(instance=permission),
                "saved": True,
                "permission": permission,
            },
        )
        response["HX-Trigger"] = "rolesChanged"
        return response
    return render(
        request,
        "pages/permission_form.html",
        {"form": form, "permission": permission},
    )


@permission_required("roles", "manage")
@require_POST
def permission_delete(request: HttpRequest, permission_id) -> HttpResponse:
    permission = dashboard_permissions_list().filter(id=permission_id).first()
    if permission is None:
        raise Http404("Permission not found.")
    permission_delete_service(permission=permission)
    return htmx_trigger(event="rolesChanged")


def _dashboard_user_data(form: DashboardUserForm) -> dict:
    """Map validated dashboard form fields to the core user service contract."""
    return {
        "email": form.cleaned_data["email"],
        "phone": form.cleaned_data["phone"],
        "employee_id": form.cleaned_data["employee_id"],
        "is_staff": form.cleaned_data["is_staff"],
        "is_active": form.cleaned_data["is_active"],
        "password": form.cleaned_data.get("password") or None,
    }

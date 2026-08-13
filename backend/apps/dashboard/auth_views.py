"""Session-based authentication views for Dashboard."""

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET", "POST"])
def session_login(request: HttpRequest) -> HttpResponse:
    """
    Session-based login for web dashboard.

    Handles traditional form POST login for server-rendered pages.
    Sets Django session cookie upon successful authentication.

    GET: Render login page
    POST: Process login form
    """
    template_name = "pages/login.html"

    if request.method == "GET":
        # Redirect if already authenticated
        if request.user.is_authenticated:
            return redirect("dashboard:home")
        return render(request, template_name)

    # POST request - process login
    identifier = request.POST.get("identifier", "").strip()
    password = request.POST.get("password", "")
    remember_me = request.POST.get("remember_me") == "on"

    if not identifier or not password:
        return render(
            request,
            template_name,
            {"error": "Please provide both identifier and password."}
        )

    user = authenticate(request, identifier=identifier, password=password)

    if user is None:
        return render(
            request,
            template_name,
            {"error": "Invalid credentials."}
        )

    if not user.is_active:
        return render(
            request,
            template_name,
            {"error": "Your account is inactive."}
        )

    # Login successful - create session
    login(request, user)

    # Configure session expiry based on remember_me
    if not remember_me:
        # Session expires when browser closes
        request.session.set_expiry(0)
    else:
        # Session lasts for 2 weeks (default)
        request.session.set_expiry(1209600)

    # Redirect to next URL or dashboard home
    next_url = request.GET.get("next") or request.POST.get("next")
    if next_url and next_url.startswith("/"):
        return redirect(next_url)
    return redirect("dashboard:home")


@require_http_methods(["POST"])
@login_required
def session_logout(request: HttpRequest) -> HttpResponse:
    """
    Session-based logout for web dashboard.

    Clears Django session and redirects to login page.
    """
    logout(request)
    return redirect("dashboard:login")


@require_http_methods(["GET"])
def check_session(request: HttpRequest) -> JsonResponse:
    """
    Check if user has active session.

    Used by frontend to verify authentication status.
    """
    if request.user.is_authenticated:
        return JsonResponse({
            "authenticated": True,
            "user": {
                "id": str(request.user.id),
                "email": request.user.email,
                "name": request.user.name if hasattr(request.user, "name") else request.user.email,
                "is_staff": request.user.is_staff,
                "is_superuser": request.user.is_superuser,
            }
        })
    return JsonResponse({"authenticated": False}, status=401)

"""Hybrid authentication module for Dashboard (Session) and API (JWT)."""

from rest_framework.authentication import (
    BaseAuthentication,
)
from rest_framework.authentication import (
    SessionAuthentication as BaseSessionAuthentication,
)
from rest_framework_simplejwt.authentication import JWTAuthentication


class SessionAuthentication(BaseSessionAuthentication):
    """
    Session authentication for Dashboard views.

    Extends DRF's SessionAuthentication to work with our custom User model
    and provides proper CSRF handling for AJAX requests from the dashboard.
    """

    def authenticate(self, request):
        """
        Authenticate the request using Django session.

        Returns None if session auth is not appropriate for this request
        (e.g., API requests with Authorization header).
        """
        # Skip session auth if JWT token is present in Authorization header
        # This allows API clients to use JWT while web dashboard uses session
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Bearer "):
            return None

        return super().authenticate(request)


class HybridAuthentication(BaseAuthentication):
    """
    Hybrid authentication that tries JWT first, then falls back to Session.

    This is useful for endpoints that need to support both:
    - API clients with JWT tokens (mobile apps, external services)
    - Web dashboard with session cookies (server-rendered pages)

    Usage:
        Add to view's authentication_classes:
        authentication_classes = [HybridAuthentication]

    Priority:
        1. JWT Bearer token in Authorization header
        2. Session cookie (django session)
    """

    def authenticate(self, request):
        """Try JWT first, then session."""
        # Try JWT authentication first
        jwt_auth = JWTAuthentication()
        try:
            result = jwt_auth.authenticate(request)
            if result is not None:
                return result
        except Exception:
            pass

        # Fall back to session authentication
        session_auth = SessionAuthentication()
        try:
            return session_auth.authenticate(request)
        except Exception:
            return None

    def authenticate_header(self, request):
        """Return WWW-Authenticate header for 401 responses."""
        return 'Bearer realm="api"'

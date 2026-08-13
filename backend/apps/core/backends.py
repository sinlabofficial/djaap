from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend

User = get_user_model()


class MultiIdentifierAuthBackend(BaseBackend):
    """Authentication backend supporting email, phone, and employee_id.

    This backend allows users to authenticate using any of the following:
    - Email address
    - Phone number
    - Employee ID
    """

    def authenticate(self, request, identifier=None, password=None, **kwargs):
        """Authenticate user using identifier (email/phone/employee_id) and password."""
        identifier = identifier or kwargs.get("username") or kwargs.get("email")
        if not identifier or not password:
            return None

        user = (
            User.objects.filter(email=identifier.lower()).first()
            or User.objects.filter(phone=identifier).first()
            or User.objects.filter(employee_id=identifier).first()
        )

        if user and user.check_password(password) and user.is_active:
            return user

        return None

    def get_user(self, user_id):
        """Get user by ID, checking if user is active."""
        try:
            user = User.objects.get(id=user_id)
            if user.is_active:
                return user
        except User.DoesNotExist:
            pass
        return None

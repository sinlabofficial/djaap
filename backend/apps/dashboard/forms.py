from datetime import date
from pathlib import Path

from django import forms
from django.db.models.fields.files import FieldFile

from apps.core.models import OrganizationSettings, Permission, Role, User
from apps.platform_runtime.models import RuntimeLog, WebhookEvent


class DashboardUserForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        min_length=8,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password_confirm = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = [
            "email",
            "phone",
            "employee_id",
            "is_staff",
            "is_active",
        ]

    def __init__(self, *args, **kwargs):
        self.is_create = kwargs.get("instance") is None
        super().__init__(*args, **kwargs)
        if self.is_create:
            self.fields["password"].required = True
            self.fields["password_confirm"].required = True

        input_class = (
            "w-full rounded-lg border border-outline bg-surface-container-lowest "
            "px-3 py-2 text-sm transition-colors focus:border-transparent "
            "focus:outline-none focus:ring-2 focus:ring-primary"
        )
        checkbox_class = (
            "h-4 w-4 rounded border-outline bg-surface-container-lowest "
            "text-primary focus:ring-primary"
        )
        for name, field in self.fields.items():
            if name in {"is_staff", "is_active"}:
                field.widget.attrs.setdefault("class", checkbox_class)
            else:
                field.widget.attrs.setdefault("class", input_class)

    def clean_phone(self):
        return self.cleaned_data["phone"] or None

    def clean_employee_id(self):
        return self.cleaned_data["employee_id"] or None

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if (password or password_confirm) and password != password_confirm:
            self.add_error("password_confirm", "Passwords do not match.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class UserImportForm(forms.Form):
    file = forms.FileField(
        label="User file",
        help_text="CSV or Excel-compatible XLS file, maximum 5 MB.",
        widget=forms.ClearableFileInput(attrs={"accept": ".csv,.xls,text/csv"}),
    )

class UserProfileForm(forms.ModelForm):
    """Allow an authenticated user to update only their own profile."""

    current_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )
    new_password = forms.CharField(
        required=False,
        min_length=8,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    new_password_confirm = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = ["profile_name", "profile_photo", "presentation_mode"]
        labels = {
            "profile_name": "Profile name",
            "profile_photo": "Profile photo",
            "presentation_mode": "Presentation mode",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["profile_name"].required = True
        self.fields["profile_photo"].required = False
        self.fields["presentation_mode"].required = False
        _apply_dashboard_input_classes(self.fields)
        self.fields["profile_photo"].widget.attrs.update(
            {"accept": "image/jpeg,image/png,image/webp,image/gif"}
        )

    def clean_profile_photo(self):
        photo = self.cleaned_data.get("profile_photo")
        if photo is False:
            return False
        if photo is None:
            return None
        if photo.size > 2 * 1024 * 1024:
            raise forms.ValidationError("Profile photo must be 2 MB or smaller.")
        allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
        allowed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
        extension = Path(photo.name).suffix.lower()
        if (
            photo.content_type not in allowed_types
            or extension not in allowed_extensions
        ):
            raise forms.ValidationError(
                "Profile photo must be a JPEG, PNG, WEBP, or GIF image."
            )
        return photo

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        new_password_confirm = cleaned_data.get("new_password_confirm")
        current_password = cleaned_data.get("current_password")

        if new_password or new_password_confirm:
            if not current_password:
                self.add_error("current_password", "Current password is required.")
            elif not self.instance.check_password(current_password):
                self.add_error("current_password", "Current password is incorrect.")
            if new_password != new_password_confirm:
                self.add_error("new_password_confirm", "New passwords do not match.")

        return cleaned_data


class OrganizationSettingsForm(forms.ModelForm):
    """Validate organization identity settings managed by staff users."""

    class Meta:
        model = OrganizationSettings
        fields = [
            "organization_name",
            "logo",
            "description",
            "address",
            "phone",
            "email",
            "mobile_presentation_enabled",
            "presentation_mode",
        ]
        labels = {
            "organization_name": "Organization name",
            "logo": "Organization logo",
            "description": "Short description",
            "address": "Address",
            "phone": "Contact number",
            "email": "Contact email",
            "mobile_presentation_enabled": "Enable Mobile Presentation Mode",
            "presentation_mode": "Organization presentation default",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["mobile_presentation_enabled"].required = False
        self.fields["presentation_mode"].required = False
        _apply_dashboard_input_classes(self.fields)
        self.fields["description"].widget = forms.Textarea(
            attrs={"rows": 3, **self.fields["description"].widget.attrs}
        )
        self.fields["address"].widget = forms.Textarea(
            attrs={"rows": 3, **self.fields["address"].widget.attrs}
        )
        self.fields["logo"].widget.attrs.update(
            {"accept": "image/jpeg,image/png,image/webp,image/gif"}
        )

    def clean_organization_name(self):
        name = self.cleaned_data["organization_name"].strip()
        if not name:
            raise forms.ValidationError("Organization name is required.")
        return name

    def clean_logo(self):
        logo = self.cleaned_data.get("logo")
        if logo is False:
            return False
        if logo is None or isinstance(logo, FieldFile):
            return None
        if logo.size > 2 * 1024 * 1024:
            raise forms.ValidationError("Organization logo must be 2 MB or smaller.")
        allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
        allowed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
        extension = Path(logo.name).suffix.lower()
        if (
            logo.content_type not in allowed_types
            or extension not in allowed_extensions
        ):
            raise forms.ValidationError(
                "Organization logo must be a JPEG, PNG, WEBP, or GIF image."
            )
        return logo


class RoleForm(forms.ModelForm):
    class Meta:
        model = Role
        fields = ["name", "level", "description", "presentation_mode_policy"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["presentation_mode_policy"].required = False
        _apply_dashboard_input_classes(self.fields)


class PermissionForm(forms.ModelForm):
    class Meta:
        model = Permission
        fields = ["resource", "action", "description"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_dashboard_input_classes(self.fields)


class LogFilterForm(forms.Form):
    """Validate filters for the administrator audit log view."""

    STATUS_CHOICES = (
        ("", "All statuses"),
        ("success", "Success"),
        ("failed", "Failed"),
    )
    TYPE_CHOICES = (
        ("", "All types"),
        ("0", "Create"),
        ("1", "Update"),
        ("2", "Delete"),
        ("3", "Access"),
    )

    status = forms.ChoiceField(choices=STATUS_CHOICES, required=False)
    type = forms.ChoiceField(choices=TYPE_CHOICES, required=False)
    date_from = forms.DateField(required=False, input_formats=["%Y-%m-%d"])
    date_to = forms.DateField(required=False, input_formats=["%Y-%m-%d"])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_dashboard_input_classes(self.fields)
        self.fields["date_from"].widget = forms.DateInput(
            attrs={"type": "date", **self.fields["date_from"].widget.attrs}
        )
        self.fields["date_to"].widget = forms.DateInput(
            attrs={"type": "date", **self.fields["date_to"].widget.attrs}
        )

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("date_from")
        end = cleaned_data.get("date_to")
        if isinstance(start, date) and isinstance(end, date) and end < start:
            raise forms.ValidationError("End date must be on or after the start date.")
        return cleaned_data


class RuntimeLogFilterForm(forms.Form):
    """Validate filters for Background Task Runtime Logs."""

    status = forms.ChoiceField(
        choices=[("", "All statuses"), *RuntimeLog.Status.choices], required=False
    )
    event_type = forms.CharField(required=False)
    severity = forms.ChoiceField(
        choices=[
            ("", "All severities"),
            ("info", "Info"),
            ("warning", "Warning"),
            ("error", "Error"),
        ],
        required=False,
    )
    correlation_id = forms.CharField(required=False)
    date_from = forms.DateField(required=False, input_formats=["%Y-%m-%d"])
    date_to = forms.DateField(required=False, input_formats=["%Y-%m-%d"])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_dashboard_input_classes(self.fields)
        self.fields["date_from"].widget = forms.DateInput(
            attrs={"type": "date", **self.fields["date_from"].widget.attrs}
        )
        self.fields["date_to"].widget = forms.DateInput(
            attrs={"type": "date", **self.fields["date_to"].widget.attrs}
        )

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("date_from")
        end = cleaned_data.get("date_to")
        if isinstance(start, date) and isinstance(end, date) and end < start:
            raise forms.ValidationError("End date must be on or after the start date.")
        return cleaned_data


class WebhookLogFilterForm(forms.Form):
    """Validate provider and lifecycle filters for webhook logs."""

    status = forms.ChoiceField(
        choices=[("", "All statuses"), *WebhookEvent.Status.choices], required=False
    )
    provider = forms.CharField(required=False)
    external_event_id = forms.CharField(required=False)
    correlation_id = forms.CharField(required=False)
    severity = forms.ChoiceField(
        choices=[("", "All severities"), ("info", "Info"), ("warning", "Warning"), ("error", "Error")],
        required=False,
    )
    date_from = forms.DateField(required=False, input_formats=["%Y-%m-%d"])
    date_to = forms.DateField(required=False, input_formats=["%Y-%m-%d"])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_dashboard_input_classes(self.fields)
        self.fields["date_from"].widget = forms.DateInput(
            attrs={"type": "date", **self.fields["date_from"].widget.attrs}
        )
        self.fields["date_to"].widget = forms.DateInput(
            attrs={"type": "date", **self.fields["date_to"].widget.attrs}
        )

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("date_from")
        end = cleaned_data.get("date_to")
        if isinstance(start, date) and isinstance(end, date) and end < start:
            raise forms.ValidationError("End date must be on or after the start date.")
        return cleaned_data


class RealtimeLogFilterForm(forms.Form):
    """Validate category and lifecycle filters for realtime Runtime Logs."""

    category = forms.CharField(required=False)
    event_type = forms.CharField(required=False)
    status = forms.ChoiceField(
        choices=[("", "All statuses"), *RuntimeLog.Status.choices], required=False
    )
    severity = forms.ChoiceField(
        choices=[("", "All severities"), ("info", "Info"), ("warning", "Warning"), ("error", "Error")],
        required=False,
    )
    provider = forms.CharField(required=False)
    external_event_id = forms.CharField(required=False)
    correlation_id = forms.CharField(required=False)
    date_from = forms.DateField(required=False, input_formats=["%Y-%m-%d"])
    date_to = forms.DateField(required=False, input_formats=["%Y-%m-%d"])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_dashboard_input_classes(self.fields)
        self.fields["date_from"].widget = forms.DateInput(
            attrs={"type": "date", **self.fields["date_from"].widget.attrs}
        )
        self.fields["date_to"].widget = forms.DateInput(
            attrs={"type": "date", **self.fields["date_to"].widget.attrs}
        )

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("date_from")
        end = cleaned_data.get("date_to")
        if isinstance(start, date) and isinstance(end, date) and end < start:
            raise forms.ValidationError("End date must be on or after the start date.")
        return cleaned_data


class UserRoleAssignForm(forms.Form):
    role = forms.ModelChoiceField(queryset=Role.objects.none())

    def __init__(self, *args, user: User, **kwargs):
        super().__init__(*args, **kwargs)
        assigned_role_ids = user.user_roles.filter(deleted__isnull=True).values_list(
            "role_id", flat=True
        )
        self.fields["role"].queryset = Role.objects.filter(
            deleted__isnull=True
        ).exclude(id__in=assigned_role_ids)


def _apply_dashboard_input_classes(fields):
    input_class = (
        "w-full rounded-lg border border-outline bg-surface-container-lowest "
        "px-3 py-2 text-sm transition-colors focus:border-transparent "
        "focus:outline-none focus:ring-2 focus:ring-primary"
    )
    for field in fields.values():
        field.widget.attrs.setdefault("class", input_class)

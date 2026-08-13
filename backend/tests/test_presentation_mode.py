import pytest
from auditlog.models import LogEntry
from django.db import connection

from apps.core.models import OrganizationSettings, Role, User, UserRole
from apps.core.selectors import (
    PRESENTATION_MODE_DASHBOARD,
    PRESENTATION_MODE_DEFAULT,
    PRESENTATION_MODE_MOBILE,
    presentation_mode_resolve,
)
from apps.core.services import (
    organization_presentation_policy_update,
    role_presentation_policy_update,
    user_presentation_preference_update,
)


@pytest.mark.django_db
def test_presentation_policy_fields_are_migrated():
    table_names = connection.introspection.table_names()
    assert OrganizationSettings._meta.db_table in table_names
    assert User._meta.get_field("presentation_mode").default == PRESENTATION_MODE_DEFAULT
    assert Role._meta.get_field("presentation_mode_policy").default == PRESENTATION_MODE_DEFAULT


@pytest.mark.django_db
def test_resolver_defaults_to_dashboard_when_feature_is_disabled():
    user = User.objects.create_user(email="mode-default@example.com", password="pass")

    decision = presentation_mode_resolve(user=user)

    assert decision.mode == PRESENTATION_MODE_DASHBOARD
    assert decision.source == "dashboard_default"


@pytest.mark.django_db
def test_resolver_precedence_is_role_then_user_then_organization():
    user = User.objects.create_user(email="mode-user@example.com", password="pass")
    role = Role.objects.create(name="Mobile Operator", level=80, presentation_mode_policy=PRESENTATION_MODE_MOBILE)
    UserRole.objects.create(user=user, role=role)
    organization = OrganizationSettings.objects.create(
        mobile_presentation_enabled=True,
        presentation_mode=PRESENTATION_MODE_DASHBOARD,
    )
    user.presentation_mode = PRESENTATION_MODE_DASHBOARD
    user.save(update_fields=["presentation_mode", "updated"])

    forced = presentation_mode_resolve(user=user, organization=organization)
    assert forced.mode == PRESENTATION_MODE_MOBILE
    assert forced.source == "role_policy"
    assert forced.forced is True

    role.presentation_mode_policy = PRESENTATION_MODE_DEFAULT
    role.save(update_fields=["presentation_mode_policy", "updated"])
    user.presentation_mode = PRESENTATION_MODE_MOBILE
    user.save(update_fields=["presentation_mode", "updated"])

    preferred = presentation_mode_resolve(user=user, organization=organization)
    assert preferred.mode == PRESENTATION_MODE_MOBILE
    assert preferred.source == "user_preference"

    user.presentation_mode = PRESENTATION_MODE_DEFAULT
    user.save(update_fields=["presentation_mode", "updated"])
    organization.presentation_mode = PRESENTATION_MODE_MOBILE
    organization.save(update_fields=["presentation_mode", "updated"])

    inherited = presentation_mode_resolve(user=user, organization=organization)
    assert inherited.mode == PRESENTATION_MODE_MOBILE
    assert inherited.source == "organization_default"


@pytest.mark.django_db
def test_policy_services_update_only_policy_and_create_audit_entries():
    actor = User.objects.create_user(email="mode-admin@example.com", password="pass", is_staff=True)
    user = User.objects.create_user(email="mode-target@example.com", password="pass")
    role = Role.objects.create(name="Flexible Operator", level=20)

    organization = organization_presentation_policy_update(
        actor=actor,
        presentation_mode=PRESENTATION_MODE_MOBILE,
        mobile_presentation_enabled=True,
    )
    user_presentation_preference_update(user=user, presentation_mode=PRESENTATION_MODE_MOBILE)
    role_presentation_policy_update(
        actor=actor,
        role=role,
        presentation_mode=PRESENTATION_MODE_MOBILE,
    )

    assert organization.presentation_mode == PRESENTATION_MODE_MOBILE
    assert user.presentation_mode == PRESENTATION_MODE_MOBILE
    assert role.presentation_mode_policy == PRESENTATION_MODE_MOBILE
    assert LogEntry.objects.filter(actor=actor).count() >= 2
    assert LogEntry.objects.filter(actor=user).count() >= 1

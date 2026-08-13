"""Regression tests for the public application root route."""

from django.test import Client
from django.urls import reverse


def test_root_redirects_to_dashboard_login():
    response = Client().get("/")

    assert response.status_code == 302
    assert response["Location"] == reverse("dashboard:login")

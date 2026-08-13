import pytest
from django.core.cache import cache
from django.test import Client


@pytest.fixture(autouse=True)
def clear_test_cache():
    """Keep throttle/cache state from leaking between tests."""
    cache.clear()


@pytest.fixture
def api_client():
    """Provide Django test client."""
    return Client()


@pytest.fixture
def user_data():
    """Provide sample user data for tests."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpass123"
    }

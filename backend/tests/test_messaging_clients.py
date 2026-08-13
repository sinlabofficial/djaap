"""Tests for messaging gateway clients."""

import pytest

from apps.core.clients.messaging.base import (
    GenericMessagingGateway,
    MessagingConfig,
)


class TestMessagingConfig:
    """Tests for MessagingConfig."""

    def test_config_initialization(self):
        """Test MessagingConfig initialization."""
        config = MessagingConfig(
            api_key="test-key",
            api_secret="test-secret",
            base_url="https://api.messaging.com",
            webhook_secret="webhook-secret",
            sender_phone="+1234567890"
        )

        assert config.api_key == "test-key"
        assert config.api_secret == "test-secret"
        assert config.base_url == "https://api.messaging.com"
        assert config.webhook_secret == "webhook-secret"
        assert config.sender_phone == "+1234567890"

    def test_config_optional_fields(self):
        """Test MessagingConfig with optional fields as None."""
        config = MessagingConfig(
            api_key="test-key"
        )

        assert config.api_key == "test-key"
        assert config.api_secret is None
        assert config.base_url == ""
        assert config.webhook_secret is None
        assert config.sender_phone is None


class TestGenericMessagingGateway:
    """Tests for GenericMessagingGateway abstract class."""

    def test_is_abstract(self):
        """Test that GenericMessagingGateway is abstract."""
        with pytest.raises(TypeError):
            GenericMessagingGateway()

"""Tests for payment gateway clients."""


import pytest

from apps.core.clients.payment.base import GenericPaymentGateway
from apps.core.clients.payment.midtrans import (
    MidtransMockClient,
    MidtransPaymentClient,
)


class TestMidtransMockClient:
    """Tests for MidtransMockClient."""

    @pytest.mark.asyncio
    async def test_mock_charge(self):
        """Test mock charge method."""
        client = MidtransMockClient()
        result = await client.charge(
            amount=100000,
            order_id="ORDER-123",
            customer_name="John Doe",
            customer_email="john@example.com"
        )

        assert result["transaction_id"] == "mock-transaction-id"
        assert result["order_id"] == "ORDER-123"
        assert result["gross_amount"] == 100000
        assert result["transaction_status"] == "pending"
        assert result["payment_type"] == "bank_transfer"

    @pytest.mark.asyncio
    async def test_mock_cancel(self):
        """Test mock cancel method."""
        client = MidtransMockClient()
        result = await client.cancel("txn-123")

        assert result["transaction_id"] == "txn-123"
        assert result["transaction_status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_mock_status(self):
        """Test mock status method."""
        client = MidtransMockClient()
        result = await client.status("txn-123")

        assert result["transaction_id"] == "txn-123"
        assert result["transaction_status"] == "settlement"


class TestMidtransPaymentClient:
    """Tests for MidtransPaymentClient."""

    def test_initialization_sandbox(self):
        """Test client initialization with sandbox environment."""
        client = MidtransPaymentClient(
            server_key="test-key",
            is_production=False
        )

        assert client.server_key == "test-key"
        assert client.base_url == "https://api.sandbox.midtrans.com"
        assert "Authorization" in client.headers
        assert "Content-Type" in client.headers

    def test_initialization_production(self):
        """Test client initialization with production environment."""
        client = MidtransPaymentClient(
            server_key="prod-key",
            is_production=True
        )

        assert client.server_key == "prod-key"
        assert client.base_url == "https://api.midtrans.com"

    def test_encode_key(self):
        """Test server key encoding for Basic auth."""
        client = MidtransPaymentClient(server_key="test-key")
        encoded = client._encode_key("test-key")

        # Should be base64 encoded "test-key:"
        assert encoded == "dGVzdC1rZXk6"




class TestGenericPaymentGateway:
    """Tests for GenericPaymentGateway abstract class."""

    def test_is_abstract(self):
        """Test that GenericPaymentGateway is abstract."""
        with pytest.raises(TypeError):
            GenericPaymentGateway()

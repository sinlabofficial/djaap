from typing import Any

from ..base import BaseHTTPClient
from ..config import MIDTRANS_CONFIG
from .base import GenericPaymentGateway


class MidtransPaymentClient(GenericPaymentGateway, BaseHTTPClient):
    """
    Midtrans payment gateway implementation.

    Example usage:
        async with MidtransPaymentClient() as client:
            result = await client.charge(
                amount=100000,
                order_id="ORDER-123",
                customer_name="John Doe",
                customer_email="john@example.com"
            )
    """

    def __init__(self, server_key: str | None = None, is_production: bool = False):
        base_url = (
            "https://api.midtrans.com" if is_production
            else "https://api.sandbox.midtrans.com"
        )
        super().__init__(
            base_url=base_url,
            timeout=MIDTRANS_CONFIG.timeout
        )
        self.server_key = server_key
        self.headers["Authorization"] = f"Basic {self._encode_key(server_key or '')}"
        self.headers["Content-Type"] = "application/json"

    def _encode_key(self, key: str) -> str:
        """Encode server key for Basic auth."""
        import base64
        return base64.b64encode(f"{key}:".encode()).decode()

    async def charge(self, amount: float, order_id: str, **kwargs: Any) -> dict[str, Any]:
        """Create Midtrans charge."""
        payload = {
            "transaction_details": {
                "order_id": order_id,
                "gross_amount": amount
            },
            "customer_details": {
                "first_name": kwargs.get("customer_name", ""),
                "email": kwargs.get("customer_email", "")
            }
        }
        response = await self.post("/v2/charge", json=payload)
        return response.json()

    async def cancel(self, transaction_id: str, **kwargs: Any) -> dict[str, Any]:
        """Cancel Midtrans transaction."""
        response = await self.post(f"/v2/{transaction_id}/cancel")
        return response.json()

    async def status(self, transaction_id: str, **kwargs: Any) -> dict[str, Any]:
        """Check Midtrans transaction status."""
        response = await self.get(f"/v2/{transaction_id}/status")
        return response.json()


class MidtransMockClient(GenericPaymentGateway):
    """Mock client for testing without real API calls."""

    async def charge(self, amount: float, order_id: str, **kwargs: Any) -> dict[str, Any]:
        return {
            "transaction_id": "mock-transaction-id",
            "order_id": order_id,
            "gross_amount": amount,
            "transaction_status": "pending",
            "payment_type": "bank_transfer"
        }

    async def cancel(self, transaction_id: str, **kwargs: Any) -> dict[str, Any]:
        return {
            "transaction_id": transaction_id,
            "transaction_status": "cancelled"
        }

    async def status(self, transaction_id: str, **kwargs: Any) -> dict[str, Any]:
        return {
            "transaction_id": transaction_id,
            "transaction_status": "settlement"
        }

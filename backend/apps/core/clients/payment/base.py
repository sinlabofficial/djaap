from abc import ABC, abstractmethod
from typing import Any


class GenericPaymentGateway(ABC):
    """
    Abstract base class for payment gateway integrations.

    Implement this interface for any payment provider (Midtrans, Stripe, etc.)
    """

    @abstractmethod
    async def charge(self, amount: float, order_id: str, **kwargs: Any) -> dict[str, Any]:
        """
        Create a payment charge.

        Args:
            amount: Payment amount
            order_id: Unique order identifier
            **kwargs: Additional payment parameters

        Returns:
            Payment response data
        """
        pass

    @abstractmethod
    async def cancel(self, transaction_id: str, **kwargs: Any) -> dict[str, Any]:
        """
        Cancel a pending transaction.

        Args:
            transaction_id: Transaction to cancel
            **kwargs: Additional cancel parameters

        Returns:
            Cancel response data
        """
        pass

    @abstractmethod
    async def status(self, transaction_id: str, **kwargs: Any) -> dict[str, Any]:
        """
        Check transaction status.

        Args:
            transaction_id: Transaction to check
            **kwargs: Additional status parameters

        Returns:
            Status response data
        """
        pass

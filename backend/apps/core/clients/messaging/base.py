from abc import ABC, abstractmethod
from typing import Any


class GenericMessagingGateway(ABC):
    """
    Abstract base class for messaging/WhatsApp gateway integrations.

    Implement this interface for any messaging provider (Twilio,
    WhatsApp Business API, etc.)
    """

    @abstractmethod
    async def send_message(self, to: str, message: str, **kwargs: Any) -> dict[str, Any]:
        """
        Send a message.

        Args:
            to: Recipient phone number (with country code)
            message: Message content
            **kwargs: Additional message parameters

        Returns:
            Send response data
        """
        pass

    @abstractmethod
    async def get_status(self, message_id: str, **kwargs: Any) -> dict[str, Any]:
        """
        Check message delivery status.

        Args:
            message_id: Message to check
            **kwargs: Additional status parameters

        Returns:
            Status response data
        """
        pass

    @abstractmethod
    async def receive_webhook(self, data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        """
        Process incoming webhook from messaging provider.

        Args:
            data: Webhook payload
            **kwargs: Additional webhook parameters

        Returns:
            Processing result
        """
        pass

    @abstractmethod
    async def verify_webhook(self, signature: str, payload: str, **kwargs: Any) -> bool:
        """
        Verify webhook signature for security.

        Args:
            signature: Provided signature
            payload: Webhook payload
            **kwargs: Additional verification parameters

        Returns:
            True if signature is valid
        """
        pass


class MessagingConfig:
    """Configuration for messaging gateway."""

    def __init__(
        self,
        api_key: str,
        api_secret: str | None = None,
        base_url: str = "",
        webhook_secret: str | None = None,
        sender_phone: str | None = None
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.webhook_secret = webhook_secret
        self.sender_phone = sender_phone

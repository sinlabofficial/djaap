from dataclasses import dataclass


@dataclass
class APIConfig:
    """Configuration for external API clients."""
    base_url: str
    api_key: str | None = None
    timeout: float = 30.0
    max_retries: int = 3


# Example configurations
MIDTRANS_CONFIG = APIConfig(
    base_url="https://api.midtrans.com",
    timeout=60.0
)

WA_GATEWAY_CONFIG = APIConfig(
    base_url="",
    timeout=30.0
)

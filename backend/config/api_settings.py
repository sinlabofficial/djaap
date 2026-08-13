from config.config import config


class APISettings:
    """API-specific settings loaded from environment."""

    @property
    def midtrans_server_key(self) -> str | None:
        return config.MIDTRANS_SERVER_KEY

    @property
    def midtrans_client_key(self) -> str | None:
        return config.MIDTRANS_CLIENT_KEY

    @property
    def midtrans_is_production(self) -> bool:
        return config.DJANGO_ENV == "production"


api_settings = APISettings()

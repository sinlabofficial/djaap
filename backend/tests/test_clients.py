"""Tests for core clients module."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from apps.core.clients.base import BaseHTTPClient
from apps.core.clients.config import MIDTRANS_CONFIG, WA_GATEWAY_CONFIG


class TestBaseHTTPClient:
    """Tests for BaseHTTPClient."""

    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test client initialization."""
        client = BaseHTTPClient(
            base_url="https://api.example.com",
            timeout=10.0,
            max_retries=5,
            headers={"Authorization": "Bearer token123"}
        )
        assert client.base_url == "https://api.example.com"
        assert client.timeout == 10.0
        assert client.max_retries == 5
        assert client.headers == {"Authorization": "Bearer token123"}
        assert client._client is None

    @pytest.mark.asyncio
    async def test_client_context_manager(self):
        """Test async context manager."""
        async with BaseHTTPClient(base_url="https://api.example.com") as client:
            assert client._client is not None
            assert isinstance(client._client, httpx.AsyncClient)

    @pytest.mark.asyncio
    async def test_get_request_success(self):
        """Test successful GET request."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        async with BaseHTTPClient(base_url="https://api.example.com") as client:
            client._client.request = AsyncMock(return_value=mock_response)
            response = await client.get("/test")

            assert response == mock_response
            client._client.request.assert_called_once_with(
                "GET", "/test"
            )

    @pytest.mark.asyncio
    async def test_post_request_success(self):
        """Test successful POST request."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        async with BaseHTTPClient(base_url="https://api.example.com") as client:
            client._client.request = AsyncMock(return_value=mock_response)
            response = await client.post("/test", json={"key": "value"})

            assert response == mock_response
            client._client.request.assert_called_once_with(
                "POST", "/test", json={"key": "value"}
            )

    @pytest.mark.asyncio
    async def test_put_request_success(self):
        """Test successful PUT request."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        async with BaseHTTPClient(base_url="https://api.example.com") as client:
            client._client.request = AsyncMock(return_value=mock_response)
            response = await client.put("/test", json={"key": "value"})

            assert response == mock_response
            client._client.request.assert_called_once_with(
                "PUT", "/test", json={"key": "value"}
            )

    @pytest.mark.asyncio
    async def test_delete_request_success(self):
        """Test successful DELETE request."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        async with BaseHTTPClient(base_url="https://api.example.com") as client:
            client._client.request = AsyncMock(return_value=mock_response)
            response = await client.delete("/test")

            assert response == mock_response
            client._client.request.assert_called_once_with(
                "DELETE", "/test"
            )

    @pytest.mark.asyncio
    async def test_request_without_client(self):
        """Test request without initializing client."""
        client = BaseHTTPClient()
        with pytest.raises(RuntimeError, match="Client not initialized"):
            await client.get("/test")

    @pytest.mark.asyncio
    async def test_retry_on_http_error(self):
        """Test retry logic on HTTP error."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        async with BaseHTTPClient(
            base_url="https://api.example.com",
            max_retries=3
        ) as client:
            # First two calls fail, third succeeds
            client._client.request = AsyncMock(
                side_effect=[
                    httpx.HTTPError("Connection error"),
                    httpx.HTTPError("Connection error"),
                    mock_response
                ]
            )

            response = await client.get("/test")
            assert response == mock_response
            assert client._client.request.call_count == 3




class TestClientConfig:
    """Tests for client configuration."""

    def test_midtrans_config_exists(self):
        """Test Midtrans config object exists."""
        assert hasattr(MIDTRANS_CONFIG, 'base_url')
        assert hasattr(MIDTRANS_CONFIG, 'api_key')
        assert hasattr(MIDTRANS_CONFIG, 'timeout')
        assert hasattr(MIDTRANS_CONFIG, 'max_retries')

    def test_messaging_config_exists(self):
        """Test messaging config object exists."""
        assert hasattr(WA_GATEWAY_CONFIG, 'base_url')
        assert hasattr(WA_GATEWAY_CONFIG, 'timeout')

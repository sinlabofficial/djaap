from typing import Any

import httpx


class BaseHTTPClient:
    """
    Base HTTP client with retry logic and connection pooling.

    Usage:
        async with BaseHTTPClient() as client:
            response = await client.get("https://api.example.com/data")
    """

    def __init__(
        self,
        base_url: str = "",
        timeout: float = 30.0,
        max_retries: int = 3,
        headers: dict[str, str] | None = None
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.headers = headers or {}
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> BaseHTTPClient:
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=self.headers
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        """Perform GET request with retry logic."""
        return await self._request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        """Perform POST request with retry logic."""
        return await self._request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs: Any) -> httpx.Response:
        """Perform PUT request with retry logic."""
        return await self._request("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        """Perform DELETE request with retry logic."""
        return await self._request("DELETE", url, **kwargs)

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Perform HTTP request with exponential backoff retry."""
        import asyncio

        last_exception: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                if not self._client:
                    raise RuntimeError("Client not initialized. Use async context manager.")

                response = await self._client.request(method, url, **kwargs)
                response.raise_for_status()
                return response

            except (httpx.HTTPError, httpx.ConnectError) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                continue

        raise last_exception or RuntimeError(f"Request failed after {self.max_retries} attempts")

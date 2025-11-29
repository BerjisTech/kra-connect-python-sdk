"""
@file http_client.py
@description HTTP client with retry logic for KRA-Connect SDK
@module kra_connect.http_client
@author KRA-Connect Team
@created 2025-01-15
"""

import logging
from typing import Optional, Dict, Any
import asyncio

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryCallState,
)

from kra_connect.config import KraConfig
from kra_connect.exceptions import (
    ApiAuthenticationError,
    ApiTimeoutError,
    ApiError,
    RateLimitExceededError,
)

logger = logging.getLogger(__name__)


class HttpClient:
    """
    HTTP client for making requests to KRA GavaConnect API.

    Handles authentication, retries, timeouts, and error handling.

    Example:
        >>> config = KraConfig(api_key="test-key")
        >>> client = HttpClient(config)
        >>> response = client.post("/verify-pin", {"pin": "P051234567A"})
    """

    def __init__(self, config: KraConfig) -> None:
        """
        Initialize HTTP client.

        Args:
            config: KRA configuration object

        Example:
            >>> config = KraConfig(api_key="test-key")
            >>> client = HttpClient(config)
        """
        self.config = config
        self.base_url = config.base_url
        self.headers = config.get_headers()

        # Create httpx client
        self._client = httpx.Client(
            base_url=self.base_url,
            headers=self.headers,
            timeout=config.timeout,
            verify=config.verify_ssl,
        )

        # Set up logging
        logging.basicConfig(level=getattr(logging, config.log_level))

    def __enter__(self) -> "HttpClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def _create_retry_decorator(self):
        """
        Create retry decorator based on configuration.

        Returns:
            Tenacity retry decorator configured with settings from config
        """
        retry_config = self.config.retry_config

        def before_retry_log(retry_state: RetryCallState) -> None:
            """Log retry attempts."""
            if retry_state.outcome and retry_state.outcome.failed:
                exception = retry_state.outcome.exception()
                logger.warning(
                    f"Retry attempt {retry_state.attempt_number} after error: {exception}"
                )

        return retry(
            stop=stop_after_attempt(retry_config.max_attempts),
            wait=wait_exponential(
                multiplier=retry_config.initial_delay,
                max=retry_config.max_delay,
            ),
            retry=(
                retry_if_exception_type(ApiTimeoutError)
                if retry_config.retry_on_timeout
                else None
            ),
            before_sleep=before_retry_log,
            reraise=True,
        )

    def _handle_response(self, response: httpx.Response, endpoint: str) -> Dict[str, Any]:
        """
        Handle API response and raise appropriate exceptions.

        Args:
            response: HTTP response object
            endpoint: API endpoint that was called

        Returns:
            Parsed JSON response data

        Raises:
            ApiAuthenticationError: If authentication fails (401)
            RateLimitExceededError: If rate limit is exceeded (429)
            ApiError: For other API errors
        """
        # Log response
        logger.debug(
            f"Response from {endpoint}: status={response.status_code}, "
            f"time={response.elapsed.total_seconds():.2f}s"
        )

        # Handle successful responses
        if response.status_code == 200:
            return response.json()

        # Handle authentication errors
        if response.status_code == 401:
            logger.error(f"Authentication failed for endpoint {endpoint}")
            raise ApiAuthenticationError("Invalid API key or authentication failed")

        # Handle rate limiting
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            logger.warning(f"Rate limit exceeded. Retry after {retry_after} seconds")
            raise RateLimitExceededError(retry_after)

        # Handle client errors
        if 400 <= response.status_code < 500:
            error_message = f"Client error: {response.status_code}"
            try:
                error_data = response.json()
                error_message = error_data.get("message", error_message)
            except Exception:
                pass

            logger.error(f"Client error for {endpoint}: {error_message}")
            raise ApiError(error_message, status_code=response.status_code)

        # Handle server errors
        if response.status_code >= 500:
            error_message = f"Server error: {response.status_code}"
            logger.error(f"Server error for {endpoint}: {error_message}")
            raise ApiError(error_message, status_code=response.status_code)

        # Unknown status code
        raise ApiError(
            f"Unexpected status code: {response.status_code}",
            status_code=response.status_code,
        )

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make a GET request to the API.

        Args:
            endpoint: API endpoint (e.g., "/verify-pin")
            params: Optional query parameters

        Returns:
            Parsed JSON response

        Raises:
            ApiAuthenticationError: If authentication fails
            ApiTimeoutError: If request times out
            ApiError: For other API errors

        Example:
            >>> client.get("/taxpayer-details", params={"pin": "P051234567A"})
            {'pin': 'P051234567A', 'name': 'John Doe', ...}
        """
        logger.info(f"GET request to {endpoint}")

        try:
            response = self._client.get(endpoint, params=params)
            return self._handle_response(response, endpoint)

        except httpx.TimeoutException as e:
            logger.error(f"Request timeout for {endpoint}: {e}")
            raise ApiTimeoutError(self.config.timeout, endpoint)

        except httpx.NetworkError as e:
            logger.error(f"Network error for {endpoint}: {e}")
            raise ApiError(f"Network error: {str(e)}")

        except httpx.HTTPError as e:
            logger.error(f"HTTP error for {endpoint}: {e}")
            raise ApiError(f"HTTP error: {str(e)}")

    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make a POST request to the API.

        Args:
            endpoint: API endpoint (e.g., "/verify-pin")
            data: Optional form data
            json_data: Optional JSON data

        Returns:
            Parsed JSON response

        Raises:
            ApiAuthenticationError: If authentication fails
            ApiTimeoutError: If request times out
            ApiError: For other API errors

        Example:
            >>> client.post("/verify-pin", json_data={"pin": "P051234567A"})
            {'pin': 'P051234567A', 'valid': True, ...}
        """
        logger.info(f"POST request to {endpoint}")

        try:
            response = self._client.post(endpoint, data=data, json=json_data)
            return self._handle_response(response, endpoint)

        except httpx.TimeoutException as e:
            logger.error(f"Request timeout for {endpoint}: {e}")
            raise ApiTimeoutError(self.config.timeout, endpoint)

        except httpx.NetworkError as e:
            logger.error(f"Network error for {endpoint}: {e}")
            raise ApiError(f"Network error: {str(e)}")

        except httpx.HTTPError as e:
            logger.error(f"HTTP error for {endpoint}: {e}")
            raise ApiError(f"HTTP error: {str(e)}")

    def put(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make a PUT request to the API.

        Args:
            endpoint: API endpoint
            json_data: Optional JSON data

        Returns:
            Parsed JSON response
        """
        logger.info(f"PUT request to {endpoint}")

        try:
            response = self._client.put(endpoint, json=json_data)
            return self._handle_response(response, endpoint)

        except httpx.TimeoutException as e:
            logger.error(f"Request timeout for {endpoint}: {e}")
            raise ApiTimeoutError(self.config.timeout, endpoint)

        except httpx.NetworkError as e:
            logger.error(f"Network error for {endpoint}: {e}")
            raise ApiError(f"Network error: {str(e)}")

        except httpx.HTTPError as e:
            logger.error(f"HTTP error for {endpoint}: {e}")
            raise ApiError(f"HTTP error: {str(e)}")

    def delete(self, endpoint: str) -> Dict[str, Any]:
        """
        Make a DELETE request to the API.

        Args:
            endpoint: API endpoint

        Returns:
            Parsed JSON response
        """
        logger.info(f"DELETE request to {endpoint}")

        try:
            response = self._client.delete(endpoint)
            return self._handle_response(response, endpoint)

        except httpx.TimeoutException as e:
            logger.error(f"Request timeout for {endpoint}: {e}")
            raise ApiTimeoutError(self.config.timeout, endpoint)

        except httpx.NetworkError as e:
            logger.error(f"Network error for {endpoint}: {e}")
            raise ApiError(f"Network error: {str(e)}")

        except httpx.HTTPError as e:
            logger.error(f"HTTP error for {endpoint}: {e}")
            raise ApiError(f"HTTP error: {str(e)}")


class AsyncHttpClient:
    """
    Async HTTP client for making requests to KRA GavaConnect API.

    Provides async/await support for concurrent operations.

    Example:
        >>> config = KraConfig(api_key="test-key")
        >>> async with AsyncHttpClient(config) as client:
        ...     response = await client.post("/verify-pin", {"pin": "P051234567A"})
    """

    def __init__(self, config: KraConfig) -> None:
        """
        Initialize async HTTP client.

        Args:
            config: KRA configuration object
        """
        self.config = config
        self.base_url = config.base_url
        self.headers = config.get_headers()

        # Create async httpx client
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=config.timeout,
            verify=config.verify_ssl,
        )

        # Set up logging
        logging.basicConfig(level=getattr(logging, config.log_level))

    async def __aenter__(self) -> "AsyncHttpClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close the async HTTP client."""
        await self._client.aclose()

    async def _handle_response(self, response: httpx.Response, endpoint: str) -> Dict[str, Any]:
        """
        Handle API response and raise appropriate exceptions.

        Args:
            response: HTTP response object
            endpoint: API endpoint that was called

        Returns:
            Parsed JSON response data
        """
        logger.debug(
            f"Response from {endpoint}: status={response.status_code}, "
            f"time={response.elapsed.total_seconds():.2f}s"
        )

        if response.status_code == 200:
            return response.json()

        if response.status_code == 401:
            logger.error(f"Authentication failed for endpoint {endpoint}")
            raise ApiAuthenticationError("Invalid API key or authentication failed")

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            logger.warning(f"Rate limit exceeded. Retry after {retry_after} seconds")
            raise RateLimitExceededError(retry_after)

        if 400 <= response.status_code < 500:
            error_message = f"Client error: {response.status_code}"
            try:
                error_data = response.json()
                error_message = error_data.get("message", error_message)
            except Exception:
                pass
            logger.error(f"Client error for {endpoint}: {error_message}")
            raise ApiError(error_message, status_code=response.status_code)

        if response.status_code >= 500:
            error_message = f"Server error: {response.status_code}"
            logger.error(f"Server error for {endpoint}: {error_message}")
            raise ApiError(error_message, status_code=response.status_code)

        raise ApiError(
            f"Unexpected status code: {response.status_code}",
            status_code=response.status_code,
        )

    async def get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make an async GET request to the API.

        Args:
            endpoint: API endpoint
            params: Optional query parameters

        Returns:
            Parsed JSON response
        """
        logger.info(f"Async GET request to {endpoint}")

        try:
            response = await self._client.get(endpoint, params=params)
            return await self._handle_response(response, endpoint)

        except httpx.TimeoutException as e:
            logger.error(f"Request timeout for {endpoint}: {e}")
            raise ApiTimeoutError(self.config.timeout, endpoint)

        except httpx.NetworkError as e:
            logger.error(f"Network error for {endpoint}: {e}")
            raise ApiError(f"Network error: {str(e)}")

        except httpx.HTTPError as e:
            logger.error(f"HTTP error for {endpoint}: {e}")
            raise ApiError(f"HTTP error: {str(e)}")

    async def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make an async POST request to the API.

        Args:
            endpoint: API endpoint
            data: Optional form data
            json_data: Optional JSON data

        Returns:
            Parsed JSON response
        """
        logger.info(f"Async POST request to {endpoint}")

        try:
            response = await self._client.post(endpoint, data=data, json=json_data)
            return await self._handle_response(response, endpoint)

        except httpx.TimeoutException as e:
            logger.error(f"Request timeout for {endpoint}: {e}")
            raise ApiTimeoutError(self.config.timeout, endpoint)

        except httpx.NetworkError as e:
            logger.error(f"Network error for {endpoint}: {e}")
            raise ApiError(f"Network error: {str(e)}")

        except httpx.HTTPError as e:
            logger.error(f"HTTP error for {endpoint}: {e}")
            raise ApiError(f"HTTP error: {str(e)}")

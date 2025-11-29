"""
@file exceptions.py
@description Custom exception classes for KRA-Connect SDK
@module kra_connect.exceptions
@author KRA-Connect Team
@created 2025-01-15
"""

from typing import Optional, Dict, Any


class KraConnectError(Exception):
    """
    Base exception for all KRA-Connect errors.

    All custom exceptions in the KRA-Connect SDK inherit from this base class.
    This allows users to catch all SDK-specific errors with a single except clause.

    Attributes:
        message: Human-readable error message
        details: Optional dictionary containing additional error context
        status_code: HTTP status code if error originated from API response
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None,
    ) -> None:
        """
        Initialize KraConnectError.

        Args:
            message: Human-readable error message
            details: Optional dictionary with additional error context
            status_code: HTTP status code if applicable

        Example:
            >>> raise KraConnectError("Operation failed", details={"reason": "timeout"})
        """
        self.message = message
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return string representation of error."""
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class InvalidPinFormatError(KraConnectError):
    """
    Raised when a PIN number format is invalid.

    The KRA PIN format should be: P followed by 9 digits and a letter.
    Example: P051234567A

    Example:
        >>> if not PIN_REGEX.match(pin):
        ...     raise InvalidPinFormatError(f"Invalid PIN: {pin}")
    """

    def __init__(self, pin_number: str) -> None:
        """
        Initialize InvalidPinFormatError.

        Args:
            pin_number: The invalid PIN that was provided

        Example:
            >>> raise InvalidPinFormatError("INVALID123")
        """
        message = (
            f"Invalid PIN format: '{pin_number}'. "
            "Expected format: P followed by 9 digits and a letter (e.g., P051234567A)"
        )
        super().__init__(message, details={"pin_number": pin_number})


class InvalidTccFormatError(KraConnectError):
    """
    Raised when a TCC (Tax Compliance Certificate) number format is invalid.

    Example:
        >>> if not TCC_REGEX.match(tcc):
        ...     raise InvalidTccFormatError(f"Invalid TCC: {tcc}")
    """

    def __init__(self, tcc_number: str) -> None:
        """
        Initialize InvalidTccFormatError.

        Args:
            tcc_number: The invalid TCC that was provided
        """
        message = f"Invalid TCC format: '{tcc_number}'. Expected format: TCC followed by digits"
        super().__init__(message, details={"tcc_number": tcc_number})


class ApiAuthenticationError(KraConnectError):
    """
    Raised when API authentication fails.

    This typically occurs when:
    - API key is missing
    - API key is invalid or expired
    - API key doesn't have required permissions

    Example:
        >>> if response.status_code == 401:
        ...     raise ApiAuthenticationError("Invalid API key")
    """

    def __init__(self, message: str = "Authentication failed") -> None:
        """
        Initialize ApiAuthenticationError.

        Args:
            message: Error message describing the authentication failure
        """
        super().__init__(message, status_code=401)


class ApiTimeoutError(KraConnectError):
    """
    Raised when an API request times out.

    This error occurs when the KRA API doesn't respond within the
    configured timeout period.

    Example:
        >>> try:
        ...     result = await client.verify_pin(pin, timeout=5)
        ... except ApiTimeoutError as e:
        ...     print(f"Request timed out after {e.timeout} seconds")
    """

    def __init__(self, timeout: float, endpoint: str) -> None:
        """
        Initialize ApiTimeoutError.

        Args:
            timeout: The timeout duration in seconds
            endpoint: The API endpoint that timed out
        """
        message = f"Request to {endpoint} timed out after {timeout} seconds"
        super().__init__(
            message,
            details={"timeout": timeout, "endpoint": endpoint},
        )
        self.timeout = timeout
        self.endpoint = endpoint


class RateLimitExceededError(KraConnectError):
    """
    Raised when API rate limit is exceeded.

    This error includes information about when the client can retry
    the request.

    Attributes:
        retry_after: Number of seconds to wait before retrying

    Example:
        >>> try:
        ...     result = client.verify_pin(pin)
        ... except RateLimitExceededError as e:
        ...     time.sleep(e.retry_after)
        ...     result = client.verify_pin(pin)  # Retry
    """

    def __init__(self, retry_after: int) -> None:
        """
        Initialize RateLimitExceededError.

        Args:
            retry_after: Number of seconds to wait before retrying
        """
        message = f"Rate limit exceeded. Retry after {retry_after} seconds"
        super().__init__(
            message,
            details={"retry_after": retry_after},
            status_code=429,
        )
        self.retry_after = retry_after


class ApiError(KraConnectError):
    """
    Raised when an API request fails for reasons other than authentication or timeout.

    This is a generic error for API failures including:
    - Server errors (5xx)
    - Invalid requests (4xx other than 401/429)
    - Network errors
    - Unexpected responses

    Example:
        >>> if response.status_code >= 500:
        ...     raise ApiError("Server error", status_code=response.status_code)
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize ApiError.

        Args:
            message: Error message
            status_code: HTTP status code
            response_data: Raw API response data
        """
        details = {"response_data": response_data} if response_data else {}
        super().__init__(message, details=details, status_code=status_code)


class ValidationError(KraConnectError):
    """
    Raised when input validation fails.

    Used for validating request parameters before making API calls.

    Example:
        >>> if not period or len(period) != 6:
        ...     raise ValidationError("Period must be in YYYYMM format")
    """

    def __init__(self, field: str, message: str) -> None:
        """
        Initialize ValidationError.

        Args:
            field: The field that failed validation
            message: Validation error message
        """
        super().__init__(
            f"Validation error for field '{field}': {message}",
            details={"field": field},
        )


class CacheError(KraConnectError):
    """
    Raised when cache operations fail.

    This error is raised when the caching layer encounters issues,
    but doesn't prevent the operation from proceeding (the SDK will
    fall back to making a direct API call).

    Example:
        >>> try:
        ...     cached_result = cache.get(key)
        ... except CacheError:
        ...     # Fall back to API call
        ...     result = await api_call()
    """

    def __init__(self, message: str, operation: str) -> None:
        """
        Initialize CacheError.

        Args:
            message: Error message
            operation: The cache operation that failed (get, set, delete, etc.)
        """
        super().__init__(message, details={"operation": operation})

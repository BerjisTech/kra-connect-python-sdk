"""
KRA-Connect Python SDK

Official Python SDK for Kenya Revenue Authority's GavaConnect API.
Provides easy-to-use interfaces for PIN verification, TCC checking,
NIL return filing, and other tax compliance operations.

Example:
    >>> from kra_connect import KraClient
    >>> client = KraClient(api_key='your-api-key')
    >>> result = client.verify_pin('P051234567A')
    >>> print(result.taxpayer_name)
"""

from kra_connect.client import KraClient, AsyncKraClient
from kra_connect.config import KraConfig, RetryConfig, CacheConfig
from kra_connect.exceptions import (
    KraConnectError,
    InvalidPinFormatError,
    InvalidTccFormatError,
    ApiAuthenticationError,
    ApiTimeoutError,
    RateLimitExceededError,
    ApiError,
)
from kra_connect.models import (
    PinVerificationResult,
    TccVerificationResult,
    EslipValidationResult,
    NilReturnResult,
    TaxpayerDetails,
)

__version__ = "0.1.0"
__author__ = "KRA-Connect Team"
__email__ = "developers@kra-connect.dev"
__license__ = "MIT"

__all__ = [
    # Clients
    "KraClient",
    "AsyncKraClient",
    # Configuration
    "KraConfig",
    "RetryConfig",
    "CacheConfig",
    # Models
    "PinVerificationResult",
    "TccVerificationResult",
    "EslipValidationResult",
    "NilReturnResult",
    "TaxpayerDetails",
    # Exceptions
    "KraConnectError",
    "InvalidPinFormatError",
    "InvalidTccFormatError",
    "ApiAuthenticationError",
    "ApiTimeoutError",
    "RateLimitExceededError",
    "ApiError",
]

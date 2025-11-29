"""
@file config.py
@description Configuration management for KRA-Connect SDK
@module kra_connect.config
@author KRA-Connect Team
@created 2025-01-15
"""

import os
from typing import Optional
from dataclasses import dataclass, field

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class RetryConfig:
    """
    Configuration for retry behavior.

    Controls how the SDK handles failed requests with exponential backoff.

    Attributes:
        max_attempts: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds before first retry (default: 1.0)
        max_delay: Maximum delay in seconds between retries (default: 30.0)
        exponential_base: Base for exponential backoff calculation (default: 2.0)
        retry_on_timeout: Whether to retry on timeout errors (default: True)
        retry_on_rate_limit: Whether to retry on rate limit errors (default: True)

    Example:
        >>> retry_config = RetryConfig(
        ...     max_attempts=5,
        ...     initial_delay=2.0,
        ...     max_delay=60.0
        ... )
        >>> client = KraClient(retry_config=retry_config)
    """

    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    retry_on_timeout: bool = True
    retry_on_rate_limit: bool = True

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.initial_delay <= 0:
            raise ValueError("initial_delay must be positive")
        if self.max_delay < self.initial_delay:
            raise ValueError("max_delay must be greater than or equal to initial_delay")
        if self.exponential_base <= 1:
            raise ValueError("exponential_base must be greater than 1")

    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given attempt number.

        Uses exponential backoff with jitter to prevent thundering herd.

        Args:
            attempt: The attempt number (0-indexed)

        Returns:
            Delay in seconds before the next retry

        Example:
            >>> config = RetryConfig()
            >>> config.get_delay(0)  # First retry
            1.0
            >>> config.get_delay(1)  # Second retry
            2.0
            >>> config.get_delay(2)  # Third retry
            4.0
        """
        import random

        delay = min(
            self.initial_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        # Add jitter (±25% of delay)
        jitter = delay * 0.25 * (2 * random.random() - 1)
        return max(0, delay + jitter)


@dataclass
class CacheConfig:
    """
    Configuration for response caching.

    Controls how API responses are cached to improve performance and
    reduce API calls.

    Attributes:
        enabled: Whether caching is enabled (default: True)
        ttl: Time-to-live in seconds for cached entries (default: 3600)
        max_size: Maximum number of cached entries (default: 1000)
        backend: Cache backend implementation (default: None for in-memory)

    Example:
        >>> cache_config = CacheConfig(
        ...     enabled=True,
        ...     ttl=7200,  # 2 hours
        ...     max_size=5000
        ... )
        >>> client = KraClient(cache_config=cache_config)
    """

    enabled: bool = True
    ttl: int = 3600  # 1 hour
    max_size: int = 1000
    backend: Optional[any] = None

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.ttl <= 0:
            raise ValueError("ttl must be positive")
        if self.max_size <= 0:
            raise ValueError("max_size must be positive")


@dataclass
class RateLimitConfig:
    """
    Configuration for rate limiting.

    Implements token bucket algorithm to control request rate.

    Attributes:
        max_requests: Maximum requests allowed in the time window (default: 100)
        window_seconds: Time window in seconds (default: 60)
        enabled: Whether rate limiting is enabled (default: True)

    Example:
        >>> rate_limit_config = RateLimitConfig(
        ...     max_requests=200,
        ...     window_seconds=60  # 200 requests per minute
        ... )
        >>> client = KraClient(rate_limit_config=rate_limit_config)
    """

    max_requests: int = 100
    window_seconds: int = 60
    enabled: bool = True

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.max_requests <= 0:
            raise ValueError("max_requests must be positive")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")


@dataclass
class KraConfig:
    """
    Main configuration for KRA-Connect SDK.

    This class holds all configuration needed to interact with the
    KRA GavaConnect API.

    Attributes:
        api_key: KRA API key (required)
        base_url: Base URL for KRA API
        timeout: Request timeout in seconds
        verify_ssl: Whether to verify SSL certificates
        retry_config: Configuration for retry behavior
        cache_config: Configuration for caching
        rate_limit_config: Configuration for rate limiting
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        user_agent: Custom user agent string

    Example:
        >>> config = KraConfig(
        ...     api_key="your-api-key",
        ...     timeout=30,
        ...     retry_config=RetryConfig(max_attempts=5)
        ... )
        >>> client = KraClient(config=config)

        Using environment variables:
        >>> # Set KRA_API_KEY in .env file
        >>> config = KraConfig.from_env()
        >>> client = KraClient(config=config)
    """

    api_key: str
    base_url: str = "https://api.kra.go.ke/gavaconnect/v1"
    timeout: float = 30.0
    verify_ssl: bool = True
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    cache_config: CacheConfig = field(default_factory=CacheConfig)
    rate_limit_config: RateLimitConfig = field(default_factory=RateLimitConfig)
    log_level: str = "INFO"
    user_agent: str = "kra-connect-python/0.1.0"

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if not self.api_key:
            raise ValueError(
                "API key is required. Set KRA_API_KEY environment variable "
                "or pass api_key parameter."
            )
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError(
                "log_level must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL"
            )

        # Ensure base_url doesn't end with slash
        self.base_url = self.base_url.rstrip("/")

    @classmethod
    def from_env(
        cls,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> "KraConfig":
        """
        Create configuration from environment variables.

        Reads configuration from environment variables with fallback to defaults.

        Environment Variables:
            - KRA_API_KEY: API key (required if not passed as parameter)
            - KRA_API_BASE_URL: Base URL for API
            - KRA_TIMEOUT: Request timeout in seconds
            - KRA_MAX_RETRIES: Maximum retry attempts
            - KRA_CACHE_ENABLED: Whether caching is enabled (true/false)
            - KRA_CACHE_TTL: Cache TTL in seconds
            - KRA_RATE_LIMIT_MAX_REQUESTS: Max requests per window
            - KRA_RATE_LIMIT_WINDOW_SECONDS: Rate limit window in seconds
            - KRA_LOG_LEVEL: Logging level

        Args:
            api_key: Optional API key (overrides environment variable)
            base_url: Optional base URL (overrides environment variable)
            timeout: Optional timeout (overrides environment variable)

        Returns:
            KraConfig instance initialized from environment

        Raises:
            ValueError: If API key is not provided and not found in environment

        Example:
            >>> # With .env file containing KRA_API_KEY
            >>> config = KraConfig.from_env()
            >>> client = KraClient(config=config)

            >>> # Override specific values
            >>> config = KraConfig.from_env(timeout=60.0)
        """
        # Get API key
        final_api_key = api_key or os.getenv("KRA_API_KEY", "")
        if not final_api_key:
            raise ValueError(
                "API key is required. Set KRA_API_KEY environment variable "
                "or pass api_key parameter."
            )

        # Get base URL
        final_base_url = base_url or os.getenv(
            "KRA_API_BASE_URL",
            "https://api.kra.go.ke/gavaconnect/v1"
        )

        # Get timeout
        final_timeout = timeout
        if final_timeout is None:
            timeout_str = os.getenv("KRA_TIMEOUT", "30.0")
            final_timeout = float(timeout_str)

        # Retry configuration
        retry_config = RetryConfig(
            max_attempts=int(os.getenv("KRA_MAX_RETRIES", "3")),
            retry_on_timeout=os.getenv("KRA_RETRY_ON_TIMEOUT", "true").lower() == "true",
            retry_on_rate_limit=os.getenv("KRA_RETRY_ON_RATE_LIMIT", "true").lower() == "true",
        )

        # Cache configuration
        cache_config = CacheConfig(
            enabled=os.getenv("KRA_CACHE_ENABLED", "true").lower() == "true",
            ttl=int(os.getenv("KRA_CACHE_TTL", "3600")),
            max_size=int(os.getenv("KRA_CACHE_MAX_SIZE", "1000")),
        )

        # Rate limit configuration
        rate_limit_config = RateLimitConfig(
            max_requests=int(os.getenv("KRA_RATE_LIMIT_MAX_REQUESTS", "100")),
            window_seconds=int(os.getenv("KRA_RATE_LIMIT_WINDOW_SECONDS", "60")),
            enabled=os.getenv("KRA_RATE_LIMIT_ENABLED", "true").lower() == "true",
        )

        # Log level
        log_level = os.getenv("KRA_LOG_LEVEL", "INFO").upper()

        return cls(
            api_key=final_api_key,
            base_url=final_base_url,
            timeout=final_timeout,
            retry_config=retry_config,
            cache_config=cache_config,
            rate_limit_config=rate_limit_config,
            log_level=log_level,
        )

    def get_headers(self) -> dict[str, str]:
        """
        Get HTTP headers for API requests.

        Returns:
            Dictionary of HTTP headers including authentication

        Example:
            >>> config = KraConfig(api_key="test-key")
            >>> headers = config.get_headers()
            >>> print(headers["Authorization"])
            Bearer test-key
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": self.user_agent,
        }

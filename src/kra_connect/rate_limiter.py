"""
@file rate_limiter.py
@description Rate limiting implementation for KRA-Connect SDK
@module kra_connect.rate_limiter
@author KRA-Connect Team
@created 2025-01-15
"""

import time
import logging
import asyncio
from typing import Optional
from collections import deque

from kra_connect.config import RateLimitConfig
from kra_connect.exceptions import RateLimitExceededError

logger = logging.getLogger(__name__)


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter implementation.

    This rate limiter uses the token bucket algorithm to control the rate
    of requests. Tokens are added to the bucket at a fixed rate, and each
    request consumes one token. If no tokens are available, the request
    is blocked until tokens become available.

    Attributes:
        max_requests: Maximum number of requests allowed
        window_seconds: Time window in seconds
        tokens: Current number of available tokens
        last_refill: Timestamp of last token refill

    Example:
        >>> config = RateLimitConfig(max_requests=100, window_seconds=60)
        >>> rate_limiter = TokenBucketRateLimiter(config)
        >>> rate_limiter.acquire()  # Blocks if rate limit exceeded
    """

    def __init__(self, config: RateLimitConfig) -> None:
        """
        Initialize rate limiter.

        Args:
            config: Rate limit configuration

        Example:
            >>> config = RateLimitConfig(max_requests=100, window_seconds=60)
            >>> rate_limiter = TokenBucketRateLimiter(config)
        """
        self.config = config
        self.enabled = config.enabled
        self.max_requests = config.max_requests
        self.window_seconds = config.window_seconds

        # Token bucket state
        self.tokens = float(config.max_requests)
        self.last_refill = time.time()

        # Calculate refill rate (tokens per second)
        self.refill_rate = config.max_requests / config.window_seconds

        logger.info(
            f"Rate limiter initialized: {self.max_requests} requests "
            f"per {self.window_seconds} seconds (enabled={self.enabled})"
        )

    def _refill_tokens(self) -> None:
        """
        Refill tokens based on elapsed time.

        Tokens are added to the bucket at a constant rate based on
        the configured refill rate.
        """
        now = time.time()
        elapsed = now - self.last_refill

        # Calculate tokens to add
        tokens_to_add = elapsed * self.refill_rate

        # Add tokens, capping at max_requests
        self.tokens = min(self.tokens + tokens_to_add, self.max_requests)
        self.last_refill = now

        logger.debug(f"Refilled tokens: {tokens_to_add:.2f}, current: {self.tokens:.2f}")

    def acquire(self, tokens: int = 1, block: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire (default: 1)
            block: Whether to block if tokens are not available (default: True)
            timeout: Maximum time to wait in seconds (default: None, wait forever)

        Returns:
            True if tokens were acquired, False otherwise

        Raises:
            RateLimitExceededError: If blocking is disabled and rate limit exceeded

        Example:
            >>> rate_limiter.acquire()  # Acquire 1 token
            True
            >>> rate_limiter.acquire(tokens=5)  # Acquire 5 tokens
            True
            >>> rate_limiter.acquire(block=False)  # Non-blocking
            False  # If rate limit exceeded
        """
        if not self.enabled:
            return True

        start_time = time.time()

        while True:
            # Refill tokens
            self._refill_tokens()

            # Check if enough tokens available
            if self.tokens >= tokens:
                self.tokens -= tokens
                logger.debug(f"Acquired {tokens} token(s), remaining: {self.tokens:.2f}")
                return True

            # If not blocking, raise exception or return False
            if not block:
                logger.warning("Rate limit exceeded (non-blocking)")
                raise RateLimitExceededError(retry_after=int(self.window_seconds))

            # Check timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    logger.warning(f"Rate limit acquisition timed out after {timeout}s")
                    return False

            # Calculate wait time
            wait_time = (tokens - self.tokens) / self.refill_rate
            wait_time = min(wait_time, 1.0)  # Don't wait more than 1 second at a time

            logger.debug(f"Waiting {wait_time:.2f}s for tokens to refill")
            time.sleep(wait_time)

    async def acquire_async(
        self, tokens: int = 1, timeout: Optional[float] = None
    ) -> bool:
        """
        Asynchronously acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire (default: 1)
            timeout: Maximum time to wait in seconds (default: None)

        Returns:
            True if tokens were acquired

        Example:
            >>> await rate_limiter.acquire_async()
            True
        """
        if not self.enabled:
            return True

        start_time = time.time()

        while True:
            # Refill tokens
            self._refill_tokens()

            # Check if enough tokens available
            if self.tokens >= tokens:
                self.tokens -= tokens
                logger.debug(f"Acquired {tokens} token(s), remaining: {self.tokens:.2f}")
                return True

            # Check timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    logger.warning(f"Rate limit acquisition timed out after {timeout}s")
                    return False

            # Calculate wait time
            wait_time = (tokens - self.tokens) / self.refill_rate
            wait_time = min(wait_time, 1.0)

            logger.debug(f"Waiting {wait_time:.2f}s for tokens to refill")
            await asyncio.sleep(wait_time)

    def reset(self) -> None:
        """
        Reset the rate limiter to initial state.

        This refills all tokens and resets the refill timestamp.

        Example:
            >>> rate_limiter.reset()
        """
        self.tokens = float(self.max_requests)
        self.last_refill = time.time()
        logger.debug("Rate limiter reset")

    def get_available_tokens(self) -> int:
        """
        Get the number of currently available tokens.

        Returns:
            Number of available tokens

        Example:
            >>> rate_limiter.get_available_tokens()
            95
        """
        self._refill_tokens()
        return int(self.tokens)

    def get_wait_time(self, tokens: int = 1) -> float:
        """
        Get estimated wait time to acquire tokens.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            Estimated wait time in seconds

        Example:
            >>> wait_time = rate_limiter.get_wait_time(tokens=10)
            >>> print(f"Wait {wait_time:.2f} seconds")
        """
        self._refill_tokens()

        if self.tokens >= tokens:
            return 0.0

        return (tokens - self.tokens) / self.refill_rate


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter implementation.

    This rate limiter uses a sliding window to track requests over time.
    It's more accurate than token bucket but uses more memory.

    Example:
        >>> config = RateLimitConfig(max_requests=100, window_seconds=60)
        >>> rate_limiter = SlidingWindowRateLimiter(config)
        >>> rate_limiter.acquire()
    """

    def __init__(self, config: RateLimitConfig) -> None:
        """
        Initialize sliding window rate limiter.

        Args:
            config: Rate limit configuration
        """
        self.config = config
        self.enabled = config.enabled
        self.max_requests = config.max_requests
        self.window_seconds = config.window_seconds

        # Deque to store request timestamps
        self.requests: deque = deque()

        logger.info(
            f"Sliding window rate limiter initialized: {self.max_requests} requests "
            f"per {self.window_seconds} seconds (enabled={self.enabled})"
        )

    def _clean_old_requests(self) -> None:
        """Remove requests older than the window."""
        now = time.time()
        cutoff = now - self.window_seconds

        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()

    def acquire(self, block: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Acquire permission to make a request.

        Args:
            block: Whether to block if rate limit exceeded
            timeout: Maximum time to wait in seconds

        Returns:
            True if permission granted, False otherwise

        Raises:
            RateLimitExceededError: If blocking is disabled and rate limit exceeded
        """
        if not self.enabled:
            return True

        start_time = time.time()

        while True:
            # Clean old requests
            self._clean_old_requests()

            # Check if we can make a request
            if len(self.requests) < self.max_requests:
                self.requests.append(time.time())
                logger.debug(
                    f"Request allowed, count: {len(self.requests)}/{self.max_requests}"
                )
                return True

            # If not blocking, raise exception
            if not block:
                logger.warning("Rate limit exceeded (non-blocking)")
                raise RateLimitExceededError(retry_after=int(self.window_seconds))

            # Check timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    logger.warning(f"Rate limit acquisition timed out after {timeout}s")
                    return False

            # Calculate wait time (time until oldest request expires)
            if self.requests:
                oldest_request = self.requests[0]
                wait_time = (oldest_request + self.window_seconds) - time.time()
                wait_time = max(0.1, min(wait_time, 1.0))
            else:
                wait_time = 0.1

            logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
            time.sleep(wait_time)

    async def acquire_async(self, timeout: Optional[float] = None) -> bool:
        """
        Asynchronously acquire permission to make a request.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if permission granted
        """
        if not self.enabled:
            return True

        start_time = time.time()

        while True:
            self._clean_old_requests()

            if len(self.requests) < self.max_requests:
                self.requests.append(time.time())
                logger.debug(
                    f"Request allowed, count: {len(self.requests)}/{self.max_requests}"
                )
                return True

            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    logger.warning(f"Rate limit acquisition timed out after {timeout}s")
                    return False

            if self.requests:
                oldest_request = self.requests[0]
                wait_time = (oldest_request + self.window_seconds) - time.time()
                wait_time = max(0.1, min(wait_time, 1.0))
            else:
                wait_time = 0.1

            logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)

    def reset(self) -> None:
        """Reset the rate limiter."""
        self.requests.clear()
        logger.debug("Rate limiter reset")

    def get_request_count(self) -> int:
        """
        Get the number of requests in the current window.

        Returns:
            Number of requests in current window
        """
        self._clean_old_requests()
        return len(self.requests)

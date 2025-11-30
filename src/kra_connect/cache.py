"""
@file cache.py
@description Caching implementation for KRA-Connect SDK
@module kra_connect.cache
@author KRA-Connect Team
@created 2025-01-15
"""

import time
import hashlib
import json
import logging
from typing import Optional, Any, Dict
from abc import ABC, abstractmethod
from dataclasses import dataclass

from cachetools import TTLCache

from kra_connect.config import CacheConfig
from kra_connect.exceptions import CacheError

logger = logging.getLogger(__name__)


class CacheBackend(ABC):
    """
    Abstract base class for cache backends.

    Allows for different cache implementations (in-memory, Redis, etc.).
    """

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int) -> None:
        """
        Store value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """
        Delete value from cache.

        Args:
            key: Cache key
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all cached values."""
        pass


class MemoryCacheBackend(CacheBackend):
    """
    In-memory cache backend using cachetools.

    Simple and fast cache implementation that stores data in memory.
    Data is lost when the process terminates.

    Example:
        >>> cache = MemoryCacheBackend(max_size=1000, ttl=3600)
        >>> cache.set("key", "value", ttl=3600)
        >>> cache.get("key")
        'value'
    """

    def __init__(self, max_size: int = 1000, ttl: int = 3600) -> None:
        """
        Initialize memory cache backend.

        Args:
            max_size: Maximum number of items to cache
            ttl: Default time-to-live in seconds
        """
        self.ttl = ttl
        self._cache: TTLCache = TTLCache(maxsize=max_size, ttl=ttl)
        logger.debug(f"Initialized memory cache with max_size={max_size}, ttl={ttl}")

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        try:
            value = self._cache.get(key)
            if value is not None:
                logger.debug(f"Cache hit for key: {key}")
            else:
                logger.debug(f"Cache miss for key: {key}")
            return value
        except Exception as e:
            logger.warning(f"Error retrieving from cache: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int) -> None:
        """
        Store value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (ignored for TTLCache, uses default)
        """
        try:
            self._cache[key] = value
            logger.debug(f"Cached value for key: {key}")
        except Exception as e:
            logger.warning(f"Error storing in cache: {e}")
            raise CacheError(f"Failed to store in cache: {e}", "set")

    def delete(self, key: str) -> None:
        """
        Delete value from cache.

        Args:
            key: Cache key
        """
        try:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Deleted cache key: {key}")
        except Exception as e:
            logger.warning(f"Error deleting from cache: {e}")

    def clear(self) -> None:
        """Clear all cached values."""
        try:
            self._cache.clear()
            logger.debug("Cache cleared")
        except Exception as e:
            logger.warning(f"Error clearing cache: {e}")


@dataclass
class CacheEntry:
    """Container for cached values with per-item TTL support."""

    value: Any
    expires_at: float

    def is_expired(self) -> bool:
        return time.time() >= self.expires_at


class CacheManager:
    """
    Manages caching operations for API responses.

    Provides a high-level interface for caching with automatic key generation.

    Example:
        >>> config = CacheConfig(enabled=True, ttl=3600)
        >>> cache_manager = CacheManager(config)
        >>> cache_manager.get_or_set("pin:P051234567A", lambda: api_call())
    """

    def __init__(self, config: CacheConfig) -> None:
        """
        Initialize cache manager.

        Args:
            config: Cache configuration

        Example:
            >>> config = CacheConfig(enabled=True, ttl=3600, max_size=1000)
            >>> cache_manager = CacheManager(config)
        """
        self.config = config
        self.enabled = config.enabled

        if config.backend:
            self.backend = config.backend
        else:
            self.backend = MemoryCacheBackend(max_size=config.max_size, ttl=config.ttl)

        logger.info(f"Cache manager initialized (enabled={self.enabled})")

    def generate_key(self, prefix: str, **kwargs: Any) -> str:
        """
        Generate a cache key from prefix and parameters.

        Args:
            prefix: Key prefix (e.g., "pin", "tcc")
            **kwargs: Additional parameters to include in key

        Returns:
            Generated cache key

        Example:
            >>> cache_manager.generate_key("pin", pin_number="P051234567A")
            'pin:a1b2c3d4...'
        """
        # Create a deterministic string from kwargs
        param_string = json.dumps(kwargs, sort_keys=True)

        # Generate hash
        hash_object = hashlib.md5(param_string.encode())
        hash_hex = hash_object.hexdigest()

        return f"{prefix}:{hash_hex}"

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or cache disabled

        Example:
            >>> value = cache_manager.get("pin:a1b2c3d4")
        """
        if not self.enabled:
            return None

        try:
            entry = self.backend.get(key)
            if entry is None:
                return None

            if isinstance(entry, CacheEntry):
                if entry.is_expired():
                    logger.debug(f"Cache entry expired for key: {key}")
                    self.delete(key)
                    return None
                return entry.value

            return entry
        except CacheError as e:
            logger.warning(f"Cache error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Store value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional time-to-live in seconds (uses config default if None)

        Example:
            >>> cache_manager.set("pin:a1b2c3d4", result, ttl=3600)
        """
        if not self.enabled:
            return

        ttl = ttl or self.config.ttl
        if ttl <= 0:
            logger.debug("Skipping cache set due to non-positive TTL")
            return

        entry = CacheEntry(value=value, expires_at=time.time() + ttl)
        try:
            self.backend.set(key, entry, ttl)
        except CacheError as e:
            logger.warning(f"Cache error: {e}")

    def delete(self, key: str) -> None:
        """
        Delete value from cache.

        Args:
            key: Cache key

        Example:
            >>> cache_manager.delete("pin:a1b2c3d4")
        """
        if not self.enabled:
            return

        try:
            self.backend.delete(key)
        except Exception as e:
            logger.warning(f"Error deleting from cache: {e}")

    def clear(self) -> None:
        """
        Clear all cached values.

        Example:
            >>> cache_manager.clear()
        """
        if not self.enabled:
            return

        try:
            self.backend.clear()
        except Exception as e:
            logger.warning(f"Error clearing cache: {e}")

    def get_or_set(self, key: str, factory_fn: callable, ttl: Optional[int] = None) -> Any:
        """
        Get value from cache or compute and store it.

        This is a convenience method that retrieves from cache if available,
        otherwise calls the factory function to compute the value and stores it.

        Args:
            key: Cache key
            factory_fn: Function to call if cache miss (should return value to cache)
            ttl: Optional time-to-live in seconds

        Returns:
            Cached or computed value

        Example:
            >>> def fetch_pin_data():
            ...     return api_client.verify_pin("P051234567A")
            >>> result = cache_manager.get_or_set("pin:P051234567A", fetch_pin_data)
        """
        # Try to get from cache
        cached_value = self.get(key)

        if cached_value is not None:
            logger.debug(f"Cache hit for key: {key}")
            return cached_value

        # Cache miss - compute value
        logger.debug(f"Cache miss for key: {key}, computing value")
        value = factory_fn()

        # Store in cache
        self.set(key, value, ttl)

        return value

    def invalidate_pattern(self, pattern: str) -> None:
        """
        Invalidate all cache keys matching a pattern.

        Note: This is a simple implementation that only works with
        MemoryCacheBackend. For Redis or other backends, you would
        need to implement pattern-based deletion.

        Args:
            pattern: Key pattern to match (e.g., "pin:*")

        Example:
            >>> cache_manager.invalidate_pattern("pin:*")
        """
        if not self.enabled:
            return

        if isinstance(self.backend, MemoryCacheBackend):
            # For memory cache, we need to iterate and delete
            keys_to_delete = [
                key for key in self.backend._cache.keys()
                if pattern.replace("*", "") in key
            ]
            for key in keys_to_delete:
                self.delete(key)
            logger.debug(f"Invalidated {len(keys_to_delete)} keys matching pattern: {pattern}")
        else:
            logger.warning("Pattern invalidation not supported for this cache backend")

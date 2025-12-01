import os

import pytest

from kra_connect.config import KraConfig, RetryConfig, CacheConfig, RateLimitConfig


def test_kra_config_requires_api_key():
    with pytest.raises(ValueError):
        KraConfig(api_key="")


def test_kra_config_from_env_reads_values(monkeypatch):
    monkeypatch.setenv("KRA_API_KEY", "env-key")
    monkeypatch.setenv("KRA_TIMEOUT", "45")
    config = KraConfig.from_env()
    assert config.api_key == "env-key"
    assert config.timeout == 45


def test_retry_cache_rate_limit_config_defaults():
    retry = RetryConfig()
    cache = CacheConfig()
    rate_limit = RateLimitConfig()

    assert retry.max_attempts == 3
    assert cache.ttl == 3600
    assert rate_limit.max_requests == 100

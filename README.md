# KRA-Connect Python SDK

> Official Python SDK for Kenya Revenue Authority's GavaConnect API

[![PyPI version](https://badge.fury.io/py/kra-connect.svg)](https://badge.fury.io/py/kra-connect)
[![Python Versions](https://img.shields.io/pypi/pyversions/kra-connect.svg)](https://pypi.org/project/kra-connect/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Coverage](https://img.shields.io/codecov/c/github/your-org/kra-connect)](https://codecov.io/gh/your-org/kra-connect)

## Features

- ✅ **PIN Verification** - Verify KRA PIN numbers
- ✅ **TCC Verification** - Check Tax Compliance Certificates
- ✅ **e-Slip Validation** - Validate electronic payment slips
- ✅ **NIL Returns** - File NIL returns programmatically
- ✅ **Taxpayer Details** - Retrieve taxpayer information
- ✅ **Obligation Management** - Manage tax obligations
- ✅ **Type Safety** - Full type hints with Pydantic models
- ✅ **Async Support** - Built-in async/await support
- ✅ **Retry Logic** - Automatic retry with exponential backoff
- ✅ **Caching** - Response caching for improved performance
- ✅ **Rate Limiting** - Built-in rate limiting

## Installation

```bash
pip install kra-connect
```

Or with Poetry:

```bash
poetry add kra-connect
```

## Quick Start

### Synchronous Usage

```python
from kra_connect import KraClient

# Initialize the client
client = KraClient(api_key="your_api_key_here")

# Verify a PIN
result = client.verify_pin("P051234567A")

if result.is_valid:
    print(f"Taxpayer: {result.taxpayer_name}")
    print(f"Status: {result.status}")
else:
    print(f"Invalid PIN: {result.error_message}")

# Check Tax Compliance Certificate
tcc_result = client.verify_tcc("TCC123456")
print(f"TCC Valid: {tcc_result.is_valid}")
print(f"Expiry Date: {tcc_result.expiry_date}")

# Get taxpayer details
details = client.get_taxpayer_details("P051234567A")
print(f"Business Name: {details.business_name}")
print(f"Registration Date: {details.registration_date}")
```

### Asynchronous Usage

```python
import asyncio
from kra_connect import AsyncKraClient

async def verify_multiple_pins():
    async with AsyncKraClient(api_key="your_api_key_here") as client:
        # Verify multiple PINs concurrently
        pins = ["P051234567A", "P051234567B", "P051234567C"]
        tasks = [client.verify_pin(pin) for pin in pins]
        results = await asyncio.gather(*tasks)

        for result in results:
            print(f"{result.pin_number}: {result.taxpayer_name}")

asyncio.run(verify_multiple_pins())
```

## Configuration

### Environment Variables

Create a `.env` file:

```env
KRA_API_KEY=your_api_key_here
KRA_API_BASE_URL=https://api.kra.go.ke/gavaconnect/v1
KRA_TIMEOUT=30
KRA_MAX_RETRIES=3
KRA_CACHE_TTL=3600
```

Then initialize the client:

```python
from kra_connect import KraClient
from dotenv import load_dotenv

load_dotenv()
client = KraClient()  # Reads from environment variables
```

### Custom Configuration

```python
from kra_connect import KraClient, KraConfig

config = KraConfig(
    api_key="your_api_key_here",
    base_url="https://api.kra.go.ke/gavaconnect/v1",
    timeout=30,
    max_retries=3,
    cache_enabled=True,
    cache_ttl=3600,
    rate_limit_max_requests=100,
    rate_limit_window_seconds=60
)

client = KraClient(config=config)
```

## API Reference

### KraClient

The main client for interacting with the KRA GavaConnect API.

#### `verify_pin(pin_number: str) -> PinVerificationResult`

Verify a KRA PIN number.

**Parameters:**
- `pin_number` (str): The PIN to verify (format: P + 9 digits + letter)

**Returns:**
- `PinVerificationResult`: Verification result with taxpayer details

**Raises:**
- `InvalidPinFormatError`: If PIN format is invalid
- `ApiAuthenticationError`: If API key is invalid
- `ApiTimeoutError`: If request times out
- `RateLimitExceededError`: If rate limit is exceeded

**Example:**
```python
result = client.verify_pin("P051234567A")
print(f"Valid: {result.is_valid}")
print(f"Name: {result.taxpayer_name}")
```

#### `verify_tcc(tcc_number: str) -> TccVerificationResult`

Verify a Tax Compliance Certificate.

**Parameters:**
- `tcc_number` (str): The TCC number to verify

**Returns:**
- `TccVerificationResult`: TCC verification result

**Example:**
```python
result = client.verify_tcc("TCC123456")
print(f"Valid: {result.is_valid}")
print(f"Expires: {result.expiry_date}")
```

#### `validate_eslip(slip_number: str) -> EslipValidationResult`

Validate an electronic payment slip.

**Parameters:**
- `slip_number` (str): The e-slip number to validate

**Returns:**
- `EslipValidationResult`: Validation result

#### `file_nil_return(pin_number: str, period: str, obligation_id: str) -> NilReturnResult`

File a NIL return for a taxpayer.

**Parameters:**
- `pin_number` (str): Taxpayer's PIN
- `period` (str): Tax period (format: YYYYMM)
- `obligation_id` (str): Obligation identifier

**Returns:**
- `NilReturnResult`: Filing result

#### `get_taxpayer_details(pin_number: str) -> TaxpayerDetails`

Retrieve detailed taxpayer information.

**Parameters:**
- `pin_number` (str): Taxpayer's PIN

**Returns:**
- `TaxpayerDetails`: Complete taxpayer information

### Error Handling

```python
from kra_connect import (
    KraClient,
    KraConnectError,
    InvalidPinFormatError,
    ApiAuthenticationError,
    ApiTimeoutError,
    RateLimitExceededError
)

try:
    result = client.verify_pin("P051234567A")
except InvalidPinFormatError as e:
    print(f"Invalid PIN format: {e}")
except ApiAuthenticationError as e:
    print(f"Authentication failed: {e}")
except ApiTimeoutError as e:
    print(f"Request timed out: {e}")
except RateLimitExceededError as e:
    print(f"Rate limit exceeded. Retry after {e.retry_after} seconds")
except KraConnectError as e:
    print(f"General error: {e}")
```

## Advanced Usage

### Batch Operations

```python
from kra_connect import KraClient

client = KraClient(api_key="your_api_key_here")

# Verify multiple PINs
pins = ["P051234567A", "P051234567B", "P051234567C"]
results = client.verify_pins_batch(pins)

for result in results:
    print(f"{result.pin_number}: {result.is_valid}")
```

### Custom Retry Logic

```python
from kra_connect import KraClient, RetryConfig

retry_config = RetryConfig(
    max_attempts=5,
    initial_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0
)

client = KraClient(
    api_key="your_api_key_here",
    retry_config=retry_config
)
```

### Caching

```python
from kra_connect import KraClient, CacheConfig

# In-memory cache
cache_config = CacheConfig(
    enabled=True,
    ttl=3600,  # 1 hour
    max_size=1000
)

# Redis cache
from kra_connect import RedisCacheBackend

cache_backend = RedisCacheBackend(url="redis://localhost:6379")
cache_config = CacheConfig(
    enabled=True,
    backend=cache_backend
)

client = KraClient(
    api_key="your_api_key_here",
    cache_config=cache_config
)
```

### Logging

```python
import logging
from kra_connect import KraClient

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

client = KraClient(api_key="your_api_key_here")
```

## Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=kra_connect --cov-report=html

# Run specific test file
pytest tests/test_pin_verification.py

# Run with verbose output
pytest -v
```

## Examples

See the [examples](./examples) directory for more usage examples:

- [Basic PIN Verification](./examples/basic_pin_verification.py)
- [Async Batch Processing](./examples/async_batch_processing.py)
- [Error Handling](./examples/error_handling.py)
- [Custom Configuration](./examples/custom_configuration.py)
- [Django Integration](./examples/django_integration.py)
- [FastAPI Integration](./examples/fastapi_integration.py)

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/your-org/kra-connect.git
cd kra-connect/packages/python-sdk

# Install Poetry
pip install poetry

# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Run tests
pytest

# Format code
black src/ tests/
isort src/ tests/

# Type checking
mypy src/

# Linting
pylint src/
```

### Running Tests

```bash
# All tests
poetry run pytest

# With coverage
poetry run pytest --cov

# Specific test
poetry run pytest tests/test_pin_verification.py -v
```

### Building Documentation

```bash
cd docs/
make html
# Open docs/_build/html/index.html
```

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for contribution guidelines.

## License

MIT License - see [LICENSE](../../LICENSE) for details.

## Support

- **Documentation**: [https://docs.kra-connect.dev/python](https://docs.kra-connect.dev/python)
- **Issues**: [GitHub Issues](https://github.com/your-org/kra-connect/issues)
- **Discord**: [Join our community](https://discord.gg/kra-connect)
- **Email**: support@kra-connect.dev

## Changelog

See [CHANGELOG.md](./CHANGELOG.md) for version history.

## Disclaimer

This is an independent project and is not officially affiliated with or endorsed by the Kenya Revenue Authority.

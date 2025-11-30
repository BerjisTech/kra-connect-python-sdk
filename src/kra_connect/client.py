"""
@file client.py
@description Main client classes for KRA-Connect SDK
@module kra_connect.client
@author KRA-Connect Team
@created 2025-01-15
"""

import asyncio
import logging
from typing import Optional, List
from datetime import datetime

from kra_connect.config import KraConfig
from kra_connect.http_client import HttpClient, AsyncHttpClient
from kra_connect.cache import CacheManager
from kra_connect.rate_limiter import TokenBucketRateLimiter
from kra_connect.validators import (
    validate_pin_format,
    validate_tcc_format,
    validate_period_format,
    validate_obligation_id,
    validate_eslip_number,
    mask_pin,
)
from kra_connect.models import (
    PinVerificationResult,
    TccVerificationResult,
    EslipValidationResult,
    NilReturnResult,
    TaxpayerDetails,
)
from kra_connect.exceptions import KraConnectError

logger = logging.getLogger(__name__)


class KraClient:
    """
    Main client for interacting with KRA GavaConnect API.

    This client provides methods for PIN verification, TCC checking,
    NIL return filing, and other tax compliance operations.

    Example:
        >>> from kra_connect import KraClient
        >>> client = KraClient(api_key='your-api-key')
        >>> result = client.verify_pin('P051234567A')
        >>> print(f"Taxpayer: {result.taxpayer_name}")

        Using context manager:
        >>> with KraClient(api_key='your-api-key') as client:
        ...     result = client.verify_pin('P051234567A')

        From environment variables:
        >>> from kra_connect import KraClient, KraConfig
        >>> config = KraConfig.from_env()
        >>> client = KraClient(config=config)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        config: Optional[KraConfig] = None,
    ) -> None:
        """
        Initialize KRA client.

        Args:
            api_key: Optional API key (overrides config)
            config: Optional configuration object

        Raises:
            ValueError: If neither api_key nor config is provided

        Example:
            >>> client = KraClient(api_key='your-api-key')

            >>> from kra_connect import KraConfig
            >>> config = KraConfig(api_key='your-api-key', timeout=60)
            >>> client = KraClient(config=config)
        """
        # Initialize configuration
        if config is None:
            if api_key is None:
                config = KraConfig.from_env()
            else:
                config = KraConfig(api_key=api_key)
        elif api_key is not None:
            config.api_key = api_key

        self.config = config

        # Initialize HTTP client
        self.http_client = HttpClient(config)

        # Initialize cache manager
        self.cache_manager = CacheManager(config.cache_config)

        # Initialize rate limiter
        self.rate_limiter = TokenBucketRateLimiter(config.rate_limit_config)

        logger.info("KRA client initialized")

    def __enter__(self) -> "KraClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()

    def close(self) -> None:
        """
        Close the client and release resources.

        Example:
            >>> client = KraClient(api_key='your-api-key')
            >>> # ... use client
            >>> client.close()
        """
        self.http_client.close()
        logger.info("KRA client closed")

    def verify_pin(self, pin_number: str) -> PinVerificationResult:
        """
        Verify a KRA PIN number.

        This method verifies if a PIN is valid and currently active in the KRA system.
        Results are cached to improve performance and reduce API calls.

        Args:
            pin_number: The PIN to verify (format: P + 9 digits + letter)

        Returns:
            PinVerificationResult with verification status and taxpayer details

        Raises:
            InvalidPinFormatError: If PIN format is invalid
            ApiAuthenticationError: If API key is invalid
            ApiTimeoutError: If request times out
            RateLimitExceededError: If rate limit is exceeded
            ApiError: For other API errors

        Example:
            >>> result = client.verify_pin('P051234567A')
            >>> if result.is_valid:
            ...     print(f"Valid PIN: {result.taxpayer_name}")
            ...     print(f"Status: {result.status}")
            ... else:
            ...     print(f"Invalid PIN: {result.error_message}")
        """
        # Validate PIN format
        normalized_pin = validate_pin_format(pin_number)

        logger.info(f"Verifying PIN: {mask_pin(normalized_pin)}")

        # Check cache
        cache_key = self.cache_manager.generate_key("pin", pin_number=normalized_pin)
        cached_result = self.cache_manager.get(cache_key)

        if cached_result:
            logger.info(f"Returning cached result for PIN: {mask_pin(normalized_pin)}")
            return cached_result

        # Acquire rate limit token
        self.rate_limiter.acquire()

        try:
            # Make API request
            response_data = self.http_client.post(
                "/verify-pin",
                json_data={"pin": normalized_pin}
            )

            # Parse response into model
            result = PinVerificationResult(
                pin_number=normalized_pin,
                is_valid=response_data.get("valid", False),
                taxpayer_name=response_data.get("taxpayer_name"),
                status=response_data.get("status"),
                registration_date=response_data.get("registration_date"),
                business_type=response_data.get("business_type"),
                postal_address=response_data.get("postal_address"),
                physical_address=response_data.get("physical_address"),
                email=response_data.get("email"),
                phone_number=response_data.get("phone_number"),
            )

            # Cache the result
            self.cache_manager.set(cache_key, result)

            logger.info(f"PIN verification completed: {mask_pin(normalized_pin)}")
            return result

        except KraConnectError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during PIN verification: {e}")
            raise KraConnectError(f"PIN verification failed: {str(e)}")

    def verify_tcc(self, tcc_number: str) -> TccVerificationResult:
        """
        Verify a Tax Compliance Certificate (TCC).

        This method checks if a TCC number is valid and currently active.

        Args:
            tcc_number: The TCC number to verify

        Returns:
            TccVerificationResult with TCC status and details

        Raises:
            InvalidTccFormatError: If TCC format is invalid
            ApiAuthenticationError: If API key is invalid
            ApiTimeoutError: If request times out
            ApiError: For other API errors

        Example:
            >>> result = client.verify_tcc('TCC123456')
            >>> if result.is_valid:
            ...     print(f"TCC valid until: {result.expiry_date}")
            ...     print(f"Taxpayer: {result.taxpayer_name}")
            ... else:
            ...     print(f"Invalid TCC: {result.error_message}")
        """
        # Validate TCC format
        normalized_tcc = validate_tcc_format(tcc_number)

        logger.info(f"Verifying TCC: {normalized_tcc}")

        # Check cache
        cache_key = self.cache_manager.generate_key("tcc", tcc_number=normalized_tcc)
        cached_result = self.cache_manager.get(cache_key)

        if cached_result:
            logger.info(f"Returning cached result for TCC: {normalized_tcc}")
            return cached_result

        # Acquire rate limit token
        self.rate_limiter.acquire()

        try:
            # Make API request
            response_data = self.http_client.post(
                "/verify-tcc",
                json_data={"tcc": normalized_tcc}
            )

            # Parse response
            result = TccVerificationResult(
                tcc_number=normalized_tcc,
                is_valid=response_data.get("valid", False),
                pin_number=response_data.get("pin_number"),
                taxpayer_name=response_data.get("taxpayer_name"),
                issue_date=response_data.get("issue_date"),
                expiry_date=response_data.get("expiry_date"),
                certificate_type=response_data.get("certificate_type"),
                status=response_data.get("status"),
            )

            # Cache the result
            self.cache_manager.set(cache_key, result)

            logger.info(f"TCC verification completed: {normalized_tcc}")
            return result

        except KraConnectError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during TCC verification: {e}")
            raise KraConnectError(f"TCC verification failed: {str(e)}")

    def validate_eslip(self, slip_number: str) -> EslipValidationResult:
        """
        Validate an electronic payment slip.

        Args:
            slip_number: The e-slip number to validate

        Returns:
            EslipValidationResult with validation status

        Raises:
            ValidationError: If slip number format is invalid
            ApiError: For API errors

        Example:
            >>> result = client.validate_eslip('ESLIP123456789')
            >>> if result.is_valid:
            ...     print(f"Payment amount: {result.amount}")
            ...     print(f"Payment date: {result.payment_date}")
        """
        # Validate slip number
        normalized_slip = validate_eslip_number(slip_number)

        logger.info(f"Validating e-slip: {normalized_slip}")

        # Acquire rate limit token
        self.rate_limiter.acquire()

        try:
            # Make API request
            response_data = self.http_client.post(
                "/validate-eslip",
                json_data={"slip_number": normalized_slip}
            )

            # Parse response
            result = EslipValidationResult(
                slip_number=normalized_slip,
                is_valid=response_data.get("valid", False),
                pin_number=response_data.get("pin_number"),
                amount=response_data.get("amount"),
                payment_date=response_data.get("payment_date"),
                payment_reference=response_data.get("payment_reference"),
                obligation_type=response_data.get("obligation_type"),
                tax_period=response_data.get("tax_period"),
                status=response_data.get("status"),
            )

            logger.info(f"E-slip validation completed: {normalized_slip}")
            return result

        except KraConnectError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during e-slip validation: {e}")
            raise KraConnectError(f"E-slip validation failed: {str(e)}")

    def file_nil_return(
        self,
        pin_number: str,
        period: str,
        obligation_id: str
    ) -> NilReturnResult:
        """
        File a NIL return for a taxpayer.

        Args:
            pin_number: Taxpayer's PIN
            period: Tax period in YYYYMM format (e.g., '202401')
            obligation_id: Obligation identifier

        Returns:
            NilReturnResult with filing status

        Raises:
            InvalidPinFormatError: If PIN format is invalid
            ValidationError: If period or obligation_id format is invalid
            ApiError: For API errors

        Example:
            >>> result = client.file_nil_return(
            ...     pin_number='P051234567A',
            ...     period='202401',
            ...     obligation_id='OBL123456'
            ... )
            >>> if result.is_successful:
            ...     print(f"NIL return filed successfully")
            ...     print(f"Reference: {result.submission_reference}")
        """
        # Validate inputs
        normalized_pin = validate_pin_format(pin_number)
        validated_period = validate_period_format(period)
        validated_obligation_id = validate_obligation_id(obligation_id)

        logger.info(
            f"Filing NIL return for PIN: {mask_pin(normalized_pin)}, "
            f"period: {validated_period}"
        )

        # Acquire rate limit token
        self.rate_limiter.acquire()

        try:
            # Make API request
            response_data = self.http_client.post(
                "/file-nil-return",
                json_data={
                    "pin": normalized_pin,
                    "period": validated_period,
                    "obligation_id": validated_obligation_id,
                }
            )

            # Parse response
            result = NilReturnResult(
                pin_number=normalized_pin,
                period=validated_period,
                obligation_id=validated_obligation_id,
                submission_reference=response_data.get("submission_reference"),
                submission_date=response_data.get("submission_date"),
                is_successful=response_data.get("success", False),
                acknowledgement_receipt=response_data.get("acknowledgement_receipt"),
            )

            logger.info(f"NIL return filing completed for PIN: {mask_pin(normalized_pin)}")
            return result

        except KraConnectError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during NIL return filing: {e}")
            raise KraConnectError(f"NIL return filing failed: {str(e)}")

    def get_taxpayer_details(self, pin_number: str) -> TaxpayerDetails:
        """
        Retrieve detailed taxpayer information.

        Args:
            pin_number: Taxpayer's PIN

        Returns:
            TaxpayerDetails with comprehensive taxpayer information

        Raises:
            InvalidPinFormatError: If PIN format is invalid
            ApiError: For API errors

        Example:
            >>> details = client.get_taxpayer_details('P051234567A')
            >>> print(f"Business: {details.business_name}")
            >>> print(f"Status: {details.status}")
            >>> for obligation in details.tax_obligations:
            ...     print(f"Obligation: {obligation.obligation_type}")
        """
        # Validate PIN format
        normalized_pin = validate_pin_format(pin_number)

        logger.info(f"Retrieving taxpayer details for PIN: {mask_pin(normalized_pin)}")

        # Check cache
        cache_key = self.cache_manager.generate_key("taxpayer", pin_number=normalized_pin)
        cached_result = self.cache_manager.get(cache_key)

        if cached_result:
            logger.info(f"Returning cached taxpayer details for PIN: {mask_pin(normalized_pin)}")
            return cached_result

        # Acquire rate limit token
        self.rate_limiter.acquire()

        try:
            # Make API request
            response_data = self.http_client.get(
                f"/taxpayer-details/{normalized_pin}"
            )

            # Parse response
            result = TaxpayerDetails(**response_data)

            # Cache the result (shorter TTL for taxpayer details)
            self.cache_manager.set(cache_key, result, ttl=1800)  # 30 minutes

            logger.info(f"Taxpayer details retrieved for PIN: {mask_pin(normalized_pin)}")
            return result

        except KraConnectError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving taxpayer details: {e}")
            raise KraConnectError(f"Failed to retrieve taxpayer details: {str(e)}")

    def verify_pins_batch(self, pin_numbers: List[str]) -> List[PinVerificationResult]:
        """
        Verify multiple PINs in batch.

        This method verifies multiple PINs sequentially. For async batch processing,
        use AsyncKraClient.

        Args:
            pin_numbers: List of PIN numbers to verify

        Returns:
            List of PinVerificationResult objects

        Example:
            >>> pins = ['P051234567A', 'P051234567B', 'P051234567C']
            >>> results = client.verify_pins_batch(pins)
            >>> for result in results:
            ...     print(f"{result.pin_number}: {result.is_valid}")
        """
        logger.info(f"Batch verifying {len(pin_numbers)} PINs")

        results = []
        for pin in pin_numbers:
            try:
                result = self.verify_pin(pin)
                results.append(result)
            except Exception as e:
                logger.error(f"Error verifying PIN {mask_pin(pin)}: {e}")
                # Create error result
                results.append(PinVerificationResult(
                    pin_number=pin,
                    is_valid=False,
                    error_message=str(e)
                ))

        logger.info(f"Batch verification completed: {len(results)} results")
        return results


class AsyncKraClient:
    """
    Async client for KRA GavaConnect API.

    Provides async/await support for concurrent operations.

    Example:
        >>> import asyncio
        >>> from kra_connect import AsyncKraClient
        >>>
        >>> async def verify_multiple():
        ...     async with AsyncKraClient(api_key='your-api-key') as client:
        ...         pins = ['P051234567A', 'P051234567B', 'P051234567C']
        ...         tasks = [client.verify_pin(pin) for pin in pins]
        ...         results = await asyncio.gather(*tasks)
        ...         for result in results:
        ...             print(f"{result.pin_number}: {result.taxpayer_name}")
        >>>
        >>> asyncio.run(verify_multiple())
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        config: Optional[KraConfig] = None,
    ) -> None:
        """Initialize async KRA client."""
        if config is None:
            if api_key is None:
                config = KraConfig.from_env()
            else:
                config = KraConfig(api_key=api_key)
        elif api_key is not None:
            config.api_key = api_key

        self.config = config
        self.http_client = AsyncHttpClient(config)
        self.cache_manager = CacheManager(config.cache_config)
        self.rate_limiter = TokenBucketRateLimiter(config.rate_limit_config)

        logger.info("Async KRA client initialized")

    async def __aenter__(self) -> "AsyncKraClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close the async client."""
        await self.http_client.close()
        logger.info("Async KRA client closed")

    async def verify_pin(self, pin_number: str) -> PinVerificationResult:
        """
        Asynchronously verify a KRA PIN number.

        Args:
            pin_number: The PIN to verify

        Returns:
            PinVerificationResult
        """
        normalized_pin = validate_pin_format(pin_number)

        logger.info(f"Async verifying PIN: {mask_pin(normalized_pin)}")

        # Check cache
        cache_key = self.cache_manager.generate_key("pin", pin_number=normalized_pin)
        cached_result = self.cache_manager.get(cache_key)

        if cached_result:
            return cached_result

        # Acquire rate limit token
        await self.rate_limiter.acquire_async()

        try:
            response_data = await self.http_client.post(
                "/verify-pin",
                json_data={"pin": normalized_pin}
            )

            result = PinVerificationResult(
                pin_number=normalized_pin,
                is_valid=response_data.get("valid", False),
                taxpayer_name=response_data.get("taxpayer_name"),
                status=response_data.get("status"),
                registration_date=response_data.get("registration_date"),
                business_type=response_data.get("business_type"),
                postal_address=response_data.get("postal_address"),
                physical_address=response_data.get("physical_address"),
                email=response_data.get("email"),
                phone_number=response_data.get("phone_number"),
            )

            self.cache_manager.set(cache_key, result)

            logger.info(f"Async PIN verification completed: {mask_pin(normalized_pin)}")
            return result

        except KraConnectError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during async PIN verification: {e}")
            raise KraConnectError(f"PIN verification failed: {str(e)}")

    async def verify_tcc(self, tcc_number: str) -> TccVerificationResult:
        """
        Asynchronously verify a Tax Compliance Certificate.
        """
        normalized_tcc = validate_tcc_format(tcc_number)
        logger.info(f"Async verifying TCC: {normalized_tcc}")

        cache_key = self.cache_manager.generate_key("tcc", tcc_number=normalized_tcc)
        cached_result = self.cache_manager.get(cache_key)
        if cached_result:
            return cached_result

        await self.rate_limiter.acquire_async()

        try:
            response_data = await self.http_client.post(
                "/verify-tcc",
                json_data={"tcc": normalized_tcc}
            )

            result = TccVerificationResult(
                tcc_number=normalized_tcc,
                is_valid=response_data.get("valid", False),
                pin_number=response_data.get("pin_number"),
                taxpayer_name=response_data.get("taxpayer_name"),
                issue_date=response_data.get("issue_date"),
                expiry_date=response_data.get("expiry_date"),
                certificate_type=response_data.get("certificate_type"),
                status=response_data.get("status"),
            )

            self.cache_manager.set(cache_key, result)
            logger.info(f"Async TCC verification completed: {normalized_tcc}")
            return result

        except KraConnectError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during async TCC verification: {e}")
            raise KraConnectError(f"TCC verification failed: {str(e)}")

    async def validate_eslip(self, slip_number: str) -> EslipValidationResult:
        """
        Asynchronously validate an electronic payment slip.
        """
        normalized_slip = validate_eslip_number(slip_number)
        logger.info(f"Async validating e-slip: {normalized_slip}")

        await self.rate_limiter.acquire_async()

        try:
            response_data = await self.http_client.post(
                "/validate-eslip",
                json_data={"slip_number": normalized_slip}
            )

            result = EslipValidationResult(
                slip_number=normalized_slip,
                is_valid=response_data.get("valid", False),
                pin_number=response_data.get("pin_number"),
                amount=response_data.get("amount"),
                payment_date=response_data.get("payment_date"),
                payment_reference=response_data.get("payment_reference"),
                obligation_type=response_data.get("obligation_type"),
                tax_period=response_data.get("tax_period"),
                status=response_data.get("status"),
            )

            logger.info(f"Async e-slip validation completed: {normalized_slip}")
            return result

        except KraConnectError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during async e-slip validation: {e}")
            raise KraConnectError(f"E-slip validation failed: {str(e)}")

    async def file_nil_return(
        self,
        pin_number: str,
        period: str,
        obligation_id: str
    ) -> NilReturnResult:
        """
        Asynchronously file a NIL return.
        """
        normalized_pin = validate_pin_format(pin_number)
        validated_period = validate_period_format(period)
        validated_obligation_id = validate_obligation_id(obligation_id)

        logger.info(
            f"Async NIL return filing for PIN: {mask_pin(normalized_pin)}, "
            f"period: {validated_period}"
        )

        await self.rate_limiter.acquire_async()

        try:
            response_data = await self.http_client.post(
                "/file-nil-return",
                json_data={
                    "pin": normalized_pin,
                    "period": validated_period,
                    "obligation_id": validated_obligation_id,
                }
            )

            result = NilReturnResult(
                pin_number=normalized_pin,
                period=validated_period,
                obligation_id=validated_obligation_id,
                submission_reference=response_data.get("submission_reference"),
                submission_date=response_data.get("submission_date"),
                is_successful=response_data.get("success", False),
                acknowledgement_receipt=response_data.get("acknowledgement_receipt"),
            )

            logger.info(f"Async NIL return filing completed: {mask_pin(normalized_pin)}")
            return result

        except KraConnectError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during async NIL return filing: {e}")
            raise KraConnectError(f"NIL return filing failed: {str(e)}")

    async def get_taxpayer_details(self, pin_number: str) -> TaxpayerDetails:
        """
        Asynchronously retrieve taxpayer details.
        """
        normalized_pin = validate_pin_format(pin_number)
        logger.info(f"Async taxpayer details for PIN: {mask_pin(normalized_pin)}")

        cache_key = self.cache_manager.generate_key("taxpayer", pin_number=normalized_pin)
        cached_result = self.cache_manager.get(cache_key)
        if cached_result:
            return cached_result

        await self.rate_limiter.acquire_async()

        try:
            response_data = await self.http_client.get(
                f"/taxpayer-details/{normalized_pin}"
            )

            result = TaxpayerDetails(**response_data)
            self.cache_manager.set(cache_key, result, ttl=1800)
            logger.info(f"Async taxpayer details retrieved: {mask_pin(normalized_pin)}")
            return result

        except KraConnectError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving async taxpayer details: {e}")
            raise KraConnectError(f"Failed to retrieve taxpayer details: {str(e)}")

    async def verify_pins_batch(self, pin_numbers: List[str]) -> List[PinVerificationResult]:
        """
        Asynchronously verify multiple PINs concurrently.
        """

        async def _verify(pin: str) -> PinVerificationResult:
            try:
                return await self.verify_pin(pin)
            except Exception as exc:
                logger.error(f"Error verifying PIN {mask_pin(pin)}: {exc}")
                return PinVerificationResult(
                    pin_number=pin,
                    is_valid=False,
                    error_message=str(exc)
                )

        tasks = [_verify(pin) for pin in pin_numbers]
        return await asyncio.gather(*tasks)

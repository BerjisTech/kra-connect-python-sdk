"""
@file validators.py
@description Input validation functions for KRA-Connect SDK
@module kra_connect.validators
@author KRA-Connect Team
@created 2025-01-15
"""

import re
from typing import Optional
from datetime import datetime

from kra_connect.exceptions import InvalidPinFormatError, InvalidTccFormatError, ValidationError


# Regex patterns for validation
PIN_REGEX = re.compile(r"^P\d{9}[A-Z]$")
TCC_REGEX = re.compile(r"^TCC\d+$")
PERIOD_REGEX = re.compile(r"^\d{6}$")  # YYYYMM format


def validate_pin_format(pin_number: str) -> str:
    """
    Validate KRA PIN number format.

    The KRA PIN format is: P followed by 9 digits and a letter.
    Example: P051234567A

    Args:
        pin_number: The PIN number to validate

    Returns:
        Normalized PIN number (uppercase, stripped of whitespace)

    Raises:
        InvalidPinFormatError: If PIN format is invalid

    Example:
        >>> validate_pin_format("P051234567A")
        'P051234567A'
        >>> validate_pin_format("p051234567a")  # Normalizes to uppercase
        'P051234567A'
        >>> validate_pin_format("INVALID")
        InvalidPinFormatError: Invalid PIN format
    """
    if not pin_number:
        raise InvalidPinFormatError("PIN number is required")

    # Normalize: strip whitespace and convert to uppercase
    normalized_pin = pin_number.strip().upper()

    # Validate format
    if not PIN_REGEX.match(normalized_pin):
        raise InvalidPinFormatError(normalized_pin)

    return normalized_pin


def validate_tcc_format(tcc_number: str) -> str:
    """
    Validate Tax Compliance Certificate (TCC) number format.

    The TCC format is: TCC followed by digits.
    Example: TCC123456

    Args:
        tcc_number: The TCC number to validate

    Returns:
        Normalized TCC number (uppercase, stripped of whitespace)

    Raises:
        InvalidTccFormatError: If TCC format is invalid

    Example:
        >>> validate_tcc_format("TCC123456")
        'TCC123456'
        >>> validate_tcc_format("tcc123456")  # Normalizes to uppercase
        'TCC123456'
        >>> validate_tcc_format("INVALID")
        InvalidTccFormatError: Invalid TCC format
    """
    if not tcc_number:
        raise InvalidTccFormatError("TCC number is required")

    # Normalize: strip whitespace and convert to uppercase
    normalized_tcc = tcc_number.strip().upper()

    # Validate format
    if not TCC_REGEX.match(normalized_tcc):
        raise InvalidTccFormatError(normalized_tcc)

    return normalized_tcc


def validate_period_format(period: str) -> str:
    """
    Validate tax period format.

    The period format is: YYYYMM (year and month).
    Example: 202401 for January 2024

    Args:
        period: The period string to validate

    Returns:
        Validated period string

    Raises:
        ValidationError: If period format is invalid

    Example:
        >>> validate_period_format("202401")
        '202401'
        >>> validate_period_format("2024-01")
        ValidationError: Period must be in YYYYMM format
        >>> validate_period_format("202413")
        ValidationError: Invalid month (must be 01-12)
    """
    if not period:
        raise ValidationError("period", "Period is required")

    # Remove any whitespace
    period = period.strip()

    # Check basic format
    if not PERIOD_REGEX.match(period):
        raise ValidationError(
            "period",
            "Period must be in YYYYMM format (e.g., 202401 for January 2024)"
        )

    # Validate year and month
    year = int(period[:4])
    month = int(period[4:])

    if year < 2000 or year > 2100:
        raise ValidationError("period", "Year must be between 2000 and 2100")

    if month < 1 or month > 12:
        raise ValidationError("period", "Month must be between 01 and 12")

    return period


def validate_obligation_id(obligation_id: str) -> str:
    """
    Validate obligation ID.

    Args:
        obligation_id: The obligation ID to validate

    Returns:
        Validated obligation ID

    Raises:
        ValidationError: If obligation ID is invalid

    Example:
        >>> validate_obligation_id("OBL123456")
        'OBL123456'
        >>> validate_obligation_id("")
        ValidationError: Obligation ID is required
    """
    if not obligation_id:
        raise ValidationError("obligation_id", "Obligation ID is required")

    obligation_id = obligation_id.strip()

    if len(obligation_id) < 3:
        raise ValidationError(
            "obligation_id",
            "Obligation ID must be at least 3 characters"
        )

    return obligation_id


def validate_eslip_number(slip_number: str) -> str:
    """
    Validate electronic slip number.

    Args:
        slip_number: The e-slip number to validate

    Returns:
        Validated slip number

    Raises:
        ValidationError: If slip number is invalid

    Example:
        >>> validate_eslip_number("ESLIP123456789")
        'ESLIP123456789'
        >>> validate_eslip_number("")
        ValidationError: E-slip number is required
    """
    if not slip_number:
        raise ValidationError("slip_number", "E-slip number is required")

    slip_number = slip_number.strip()

    if len(slip_number) < 5:
        raise ValidationError(
            "slip_number",
            "E-slip number must be at least 5 characters"
        )

    return slip_number


def validate_amount(amount: float, field_name: str = "amount") -> float:
    """
    Validate monetary amount.

    Args:
        amount: The amount to validate
        field_name: Name of the field (for error messages)

    Returns:
        Validated amount

    Raises:
        ValidationError: If amount is invalid

    Example:
        >>> validate_amount(100.50)
        100.5
        >>> validate_amount(-10)
        ValidationError: Amount must be positive
    """
    if amount is None:
        raise ValidationError(field_name, f"{field_name} is required")

    if not isinstance(amount, (int, float)):
        raise ValidationError(field_name, f"{field_name} must be a number")

    if amount < 0:
        raise ValidationError(field_name, f"{field_name} must be positive")

    return float(amount)


def validate_date_string(date_string: str, field_name: str = "date") -> str:
    """
    Validate date string format.

    Accepts ISO 8601 format (YYYY-MM-DD).

    Args:
        date_string: The date string to validate
        field_name: Name of the field (for error messages)

    Returns:
        Validated date string

    Raises:
        ValidationError: If date format is invalid

    Example:
        >>> validate_date_string("2024-01-15")
        '2024-01-15'
        >>> validate_date_string("15/01/2024")
        ValidationError: Date must be in YYYY-MM-DD format
    """
    if not date_string:
        raise ValidationError(field_name, f"{field_name} is required")

    date_string = date_string.strip()

    try:
        datetime.strptime(date_string, "%Y-%m-%d")
    except ValueError:
        raise ValidationError(
            field_name,
            f"{field_name} must be in YYYY-MM-DD format (e.g., 2024-01-15)"
        )

    return date_string


def validate_email(email: str) -> str:
    """
    Validate email address format.

    Args:
        email: Email address to validate

    Returns:
        Normalized email (lowercase, stripped)

    Raises:
        ValidationError: If email format is invalid

    Example:
        >>> validate_email("user@example.com")
        'user@example.com'
        >>> validate_email("User@Example.COM")
        'user@example.com'
        >>> validate_email("invalid-email")
        ValidationError: Invalid email format
    """
    if not email:
        raise ValidationError("email", "Email is required")

    email = email.strip().lower()

    # Basic email validation regex
    email_regex = re.compile(r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$")

    if not email_regex.match(email):
        raise ValidationError("email", "Invalid email format")

    return email


def validate_phone_number(phone_number: str) -> str:
    """
    Validate phone number format (Kenyan format).

    Accepts formats:
    - +254XXXXXXXXX (international)
    - 07XXXXXXXX or 01XXXXXXXX (local)
    - 2547XXXXXXXX or 2541XXXXXXXX (without +)

    Args:
        phone_number: Phone number to validate

    Returns:
        Normalized phone number in international format (+254XXXXXXXXX)

    Raises:
        ValidationError: If phone number format is invalid

    Example:
        >>> validate_phone_number("+254712345678")
        '+254712345678'
        >>> validate_phone_number("0712345678")
        '+254712345678'
        >>> validate_phone_number("254712345678")
        '+254712345678'
    """
    if not phone_number:
        raise ValidationError("phone_number", "Phone number is required")

    # Remove whitespace and hyphens
    phone_number = re.sub(r"[\s\-]", "", phone_number)

    # Convert to international format
    if phone_number.startswith("0"):
        # Local format (0712345678 -> +254712345678)
        phone_number = "+254" + phone_number[1:]
    elif phone_number.startswith("254") and not phone_number.startswith("+"):
        # International without + (254712345678 -> +254712345678)
        phone_number = "+" + phone_number
    elif not phone_number.startswith("+254"):
        raise ValidationError(
            "phone_number",
            "Phone number must be in Kenyan format (+254XXXXXXXXX or 07XXXXXXXX)"
        )

    # Validate final format
    kenyan_phone_regex = re.compile(r"^\+254[17]\d{8}$")
    if not kenyan_phone_regex.match(phone_number):
        raise ValidationError(
            "phone_number",
            "Invalid Kenyan phone number format (must be +254 followed by 9 digits starting with 7 or 1)"
        )

    return phone_number


def mask_pin(pin_number: str) -> str:
    """
    Mask PIN number for logging purposes.

    Shows only first 3 and last 2 characters.

    Args:
        pin_number: PIN number to mask

    Returns:
        Masked PIN number

    Example:
        >>> mask_pin("P051234567A")
        'P05******7A'
    """
    if not pin_number or len(pin_number) < 5:
        return "***"

    return f"{pin_number[:3]}{'*' * (len(pin_number) - 5)}{pin_number[-2:]}"


def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """
    Mask sensitive data for logging.

    Args:
        data: Sensitive data to mask
        visible_chars: Number of characters to keep visible at the end

    Returns:
        Masked data

    Example:
        >>> mask_sensitive_data("api_key_12345678", visible_chars=4)
        '************5678'
    """
    if not data or len(data) <= visible_chars:
        return "*" * len(data) if data else ""

    return "*" * (len(data) - visible_chars) + data[-visible_chars:]

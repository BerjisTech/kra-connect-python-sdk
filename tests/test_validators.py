import pytest

from kra_connect.validators import (
    validate_pin_format,
    validate_tcc_format,
    validate_period_format,
    validate_obligation_id,
    InvalidPinFormatError,
    InvalidTccFormatError,
    ValidationError,
)


def test_validate_pin_normalizes_uppercase():
    assert validate_pin_format("p051234567a") == "P051234567A"


def test_validate_pin_rejects_invalid():
    with pytest.raises(InvalidPinFormatError):
        validate_pin_format("INVALID")


def test_validate_tcc_accepts_prefix():
    assert validate_tcc_format("tcc123456") == "TCC123456"


def test_validate_tcc_rejects_bad_format():
    with pytest.raises(InvalidTccFormatError):
        validate_tcc_format("TC123")


def test_validate_period_allows_valid_range():
    assert validate_period_format("202401") == "202401"


def test_validate_period_rejects_bad_month():
    with pytest.raises(ValidationError):
        validate_period_format("202413")


def test_validate_obligation_id_requires_min_length():
    assert validate_obligation_id("OBL123") == "OBL123"
    with pytest.raises(ValidationError):
        validate_obligation_id("AB")

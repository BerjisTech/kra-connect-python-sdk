"""
@file models.py
@description Pydantic models for KRA-Connect SDK data structures
@module kra_connect.models
@author KRA-Connect Team
@created 2025-01-15
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class TaxpayerStatus(str, Enum):
    """Enumeration of possible taxpayer statuses."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DORMANT = "dormant"


class ObligationStatus(str, Enum):
    """Enumeration of tax obligation statuses."""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PENDING = "pending"
    OVERDUE = "overdue"


class PinVerificationResult(BaseModel):
    """
    Result of a PIN verification request.

    This model contains all information returned from a PIN verification
    including taxpayer details and verification status.

    Attributes:
        pin_number: The verified PIN number
        is_valid: Whether the PIN is valid and active
        taxpayer_name: Full name or business name of the taxpayer
        status: Current status of the taxpayer (active, inactive, etc.)
        registration_date: Date when the PIN was registered
        business_type: Type of business (individual, company, etc.)
        postal_address: Taxpayer's postal address
        physical_address: Taxpayer's physical address
        email: Contact email address
        phone_number: Contact phone number
        error_message: Error message if verification failed

    Example:
        >>> result = client.verify_pin('P051234567A')
        >>> if result.is_valid:
        ...     print(f"Taxpayer: {result.taxpayer_name}")
        ...     print(f"Status: {result.status}")
    """

    pin_number: str = Field(..., description="The KRA PIN number")
    is_valid: bool = Field(..., description="Whether the PIN is valid")
    taxpayer_name: Optional[str] = Field(None, description="Taxpayer's name")
    status: Optional[TaxpayerStatus] = Field(None, description="Taxpayer status")
    registration_date: Optional[date] = Field(None, description="PIN registration date")
    business_type: Optional[str] = Field(None, description="Type of business")
    postal_address: Optional[str] = Field(None, description="Postal address")
    physical_address: Optional[str] = Field(None, description="Physical address")
    email: Optional[str] = Field(None, description="Email address")
    phone_number: Optional[str] = Field(None, description="Phone number")
    error_message: Optional[str] = Field(None, description="Error message if verification failed")
    verified_at: datetime = Field(default_factory=datetime.now, description="Verification timestamp")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
        }


class TccVerificationResult(BaseModel):
    """
    Result of a Tax Compliance Certificate (TCC) verification.

    Attributes:
        tcc_number: The TCC number
        is_valid: Whether the TCC is currently valid
        pin_number: Associated taxpayer PIN
        taxpayer_name: Name of the taxpayer
        issue_date: Date when TCC was issued
        expiry_date: Date when TCC expires
        certificate_type: Type of TCC (standard, special, etc.)
        status: Current status of the certificate
        error_message: Error message if verification failed

    Example:
        >>> result = client.verify_tcc('TCC123456')
        >>> if result.is_valid:
        ...     print(f"Valid until: {result.expiry_date}")
    """

    tcc_number: str = Field(..., description="TCC number")
    is_valid: bool = Field(..., description="Whether TCC is valid")
    pin_number: Optional[str] = Field(None, description="Associated PIN")
    taxpayer_name: Optional[str] = Field(None, description="Taxpayer name")
    issue_date: Optional[date] = Field(None, description="Issue date")
    expiry_date: Optional[date] = Field(None, description="Expiry date")
    certificate_type: Optional[str] = Field(None, description="Certificate type")
    status: Optional[str] = Field(None, description="Certificate status")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    verified_at: datetime = Field(default_factory=datetime.now, description="Verification timestamp")

    @property
    def is_expired(self) -> bool:
        """Check if the TCC has expired."""
        if self.expiry_date:
            return date.today() > self.expiry_date
        return False

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
        }


class EslipValidationResult(BaseModel):
    """
    Result of electronic payment slip validation.

    Attributes:
        slip_number: The e-slip number
        is_valid: Whether the slip is valid
        pin_number: Associated taxpayer PIN
        amount: Payment amount
        payment_date: Date of payment
        payment_reference: Payment reference number
        obligation_type: Type of tax obligation
        tax_period: Tax period for the payment
        status: Payment status
        error_message: Error message if validation failed
    """

    slip_number: str = Field(..., description="E-slip number")
    is_valid: bool = Field(..., description="Whether slip is valid")
    pin_number: Optional[str] = Field(None, description="Taxpayer PIN")
    amount: Optional[float] = Field(None, description="Payment amount")
    payment_date: Optional[date] = Field(None, description="Payment date")
    payment_reference: Optional[str] = Field(None, description="Payment reference")
    obligation_type: Optional[str] = Field(None, description="Tax obligation type")
    tax_period: Optional[str] = Field(None, description="Tax period")
    status: Optional[str] = Field(None, description="Payment status")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    validated_at: datetime = Field(default_factory=datetime.now, description="Validation timestamp")

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
        }


class NilReturnResult(BaseModel):
    """
    Result of NIL return filing.

    Attributes:
        pin_number: Taxpayer PIN
        period: Tax period (YYYYMM format)
        obligation_id: Obligation identifier
        submission_reference: Submission reference number
        submission_date: Date of submission
        is_successful: Whether filing was successful
        acknowledgement_receipt: Acknowledgement receipt number
        error_message: Error message if filing failed
    """

    pin_number: str = Field(..., description="Taxpayer PIN")
    period: str = Field(..., description="Tax period (YYYYMM)")
    obligation_id: str = Field(..., description="Obligation identifier")
    submission_reference: Optional[str] = Field(None, description="Submission reference")
    submission_date: Optional[datetime] = Field(None, description="Submission date")
    is_successful: bool = Field(..., description="Whether filing was successful")
    acknowledgement_receipt: Optional[str] = Field(None, description="Acknowledgement receipt")
    error_message: Optional[str] = Field(None, description="Error message if failed")

    @field_validator("period")
    @classmethod
    def validate_period_format(cls, value: str) -> str:
        """Validate tax period format (YYYYMM)."""
        if len(value) != 6 or not value.isdigit():
            raise ValueError("Period must be in YYYYMM format")
        year = int(value[:4])
        month = int(value[4:])
        if month < 1 or month > 12:
            raise ValueError("Month must be between 01 and 12")
        if year < 2000 or year > 2100:
            raise ValueError("Year must be between 2000 and 2100")
        return value

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class TaxObligation(BaseModel):
    """
    Represents a tax obligation.

    Attributes:
        obligation_id: Unique obligation identifier
        obligation_type: Type of tax obligation (VAT, PAYE, etc.)
        description: Description of the obligation
        frequency: Filing frequency (monthly, quarterly, etc.)
        status: Compliance status
        due_date: Next filing due date
        last_filed: Date of last filing
    """

    obligation_id: str = Field(..., description="Obligation identifier")
    obligation_type: str = Field(..., description="Obligation type")
    description: str = Field(..., description="Obligation description")
    frequency: str = Field(..., description="Filing frequency")
    status: ObligationStatus = Field(..., description="Compliance status")
    due_date: Optional[date] = Field(None, description="Next due date")
    last_filed: Optional[date] = Field(None, description="Last filing date")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {date: lambda v: v.isoformat()}


class TaxpayerDetails(BaseModel):
    """
    Comprehensive taxpayer information.

    Attributes:
        pin_number: KRA PIN number
        taxpayer_name: Full name or business name
        business_name: Registered business name
        registration_date: PIN registration date
        status: Taxpayer status
        business_type: Type of business
        postal_address: Postal address
        physical_address: Physical address
        email: Email address
        phone_number: Phone number
        tax_obligations: List of tax obligations
        compliance_status: Overall compliance status
        tcc_status: Tax Compliance Certificate status
        last_updated: Last update timestamp
    """

    pin_number: str = Field(..., description="KRA PIN number")
    taxpayer_name: str = Field(..., description="Taxpayer name")
    business_name: Optional[str] = Field(None, description="Business name")
    registration_date: Optional[date] = Field(None, description="Registration date")
    status: TaxpayerStatus = Field(..., description="Taxpayer status")
    business_type: Optional[str] = Field(None, description="Business type")
    postal_address: Optional[str] = Field(None, description="Postal address")
    physical_address: Optional[str] = Field(None, description="Physical address")
    email: Optional[str] = Field(None, description="Email address")
    phone_number: Optional[str] = Field(None, description="Phone number")
    tax_obligations: List[TaxObligation] = Field(
        default_factory=list, description="Tax obligations"
    )
    compliance_status: Optional[ObligationStatus] = Field(None, description="Compliance status")
    tcc_status: Optional[str] = Field(None, description="TCC status")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last update timestamp")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
        }

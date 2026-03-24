"""Validadores de datos externos (S11)."""

from enricher.validators.external_response import (
    AbuseIPDBResponse,
    OTXGeneralResponse,
    validate_external_response,
)

__all__ = [
    "AbuseIPDBResponse",
    "OTXGeneralResponse",
    "validate_external_response",
]

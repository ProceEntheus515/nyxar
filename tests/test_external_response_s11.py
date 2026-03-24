"""Validación de respuestas externas (S11)."""

from enricher.validators.external_response import (
    AbuseIPDBResponse,
    OTXGeneralResponse,
    validate_external_response,
)


def test_abuseipdb_valid():
    m = validate_external_response(
        {
            "ipAddress": "8.8.8.8",
            "isPublic": True,
            "abuseConfidenceScore": 0,
            "countryCode": "us",
        },
        AbuseIPDBResponse,
        "test",
    )
    assert m is not None
    assert m.countryCode == "US"


def test_abuseipdb_invalid_score():
    assert (
        validate_external_response(
            {
                "ipAddress": "8.8.8.8",
                "isPublic": True,
                "abuseConfidenceScore": 999,
            },
            AbuseIPDBResponse,
            "test",
        )
        is None
    )


def test_otx_valid_pulse():
    m = validate_external_response(
        {"pulse_info": {"count": 2, "pulses": [{"tags": ["phishing"]}]}},
        OTXGeneralResponse,
        "test",
    )
    assert m is not None
    assert m.pulse_info is not None
    assert m.pulse_info.count == 2

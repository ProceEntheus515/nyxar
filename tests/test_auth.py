"""Tests unitarios del módulo api.auth (S01)."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

# Secreto mínimo antes de importar módulos que validan al cargar
os.environ.setdefault("NYXAR_JWT_SECRET", "unit_test_secret_key_at_least_32_chars")


from api.auth.core import (  # noqa: E402
    create_access_token,
    generate_api_key,
    verify_api_key,
    verify_token,
)
from api.auth.models import User  # noqa: E402
from api.auth.roles import ROLE_HIERARCHY, Role  # noqa: E402


def test_verify_api_key_roundtrip():
    plain, digest = generate_api_key()
    assert plain.startswith("nyx_")
    assert verify_api_key(plain, digest)
    assert not verify_api_key("wrong", digest)


def test_verify_api_key_timing_safe_rejects_wrong_hash():
    _, digest = generate_api_key()
    assert not verify_api_key("nyx_fake", digest)


def test_jwt_roundtrip():
    u = User(
        id="u1",
        username="alice",
        role=Role.VIEWER,
        created_at=datetime.now(timezone.utc),
    )
    token = create_access_token(u)
    td = verify_token(token)
    assert td is not None
    assert td.username == "alice"
    assert td.role == Role.VIEWER


def test_jwt_rejects_garbage():
    assert verify_token("not.a.jwt") is None


def test_role_hierarchy_ordering():
    assert ROLE_HIERARCHY[Role.VIEWER] < ROLE_HIERARCHY[Role.ADMIN]

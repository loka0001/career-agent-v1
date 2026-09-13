import pytest

from app.domain.errors import AuthenticationError
from app.security import (
    create_session_token,
    create_signed_resource_token,
    decode_session_token,
    hash_password,
    verify_password,
    verify_signed_resource_token,
)


def test_password_hash_is_salted_and_verifiable() -> None:
    first = hash_password("a-very-long-password", salt=b"0123456789abcdef")
    second = hash_password("a-very-long-password", salt=b"abcdef0123456789")
    assert first != second
    assert verify_password("a-very-long-password", first)
    assert not verify_password("wrong-password", first)
    assert not verify_password("anything", "broken")


def test_signed_session_detects_tampering() -> None:
    token = create_session_token(
        session_id="ses_test",
        user_id="usr_test",
        email="merchant@example.com",
        store_id="demo-store",
        csrf_token="csrf",
        ttl_seconds=60,
        secret_key="secret",
    )
    claims = decode_session_token(token, "secret")
    assert claims.store_id == "demo-store"
    assert claims.user_id == "usr_test"
    with pytest.raises(AuthenticationError):
        decode_session_token(token + "tampered", "secret")
    with pytest.raises(AuthenticationError):
        decode_session_token(token, "another-secret")


def test_signed_resource_token_is_resource_bound_and_tamper_evident() -> None:
    token = create_signed_resource_token(
        "database-media:asset-1",
        ttl_seconds=60,
        secret_key="resource-secret",
    )
    assert verify_signed_resource_token(
        token,
        "database-media:asset-1",
        secret_key="resource-secret",
    )
    assert not verify_signed_resource_token(
        token,
        "database-media:asset-2",
        secret_key="resource-secret",
    )
    assert not verify_signed_resource_token(
        token + "x",
        "database-media:asset-1",
        secret_key="resource-secret",
    )

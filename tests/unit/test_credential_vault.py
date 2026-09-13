"""Credential vault key-version and rotation tests."""

from __future__ import annotations

from app.services.credential_vault import (
    configure_credential_vault,
    credential_rotation_required,
    decrypt_configured_credentials,
    encrypt_configured_credentials,
    rotate_configured_credentials,
)

TEST_APP_KEY = "test-secret-key-with-enough-entropy"


def test_old_credentials_decrypt_and_rotate_to_active_key() -> None:
    old_key = "old-integration-key-with-enough-entropy"
    new_key = "new-integration-key-with-enough-entropy"
    try:
        configure_credential_vault(old_key, key_version=1)
        old_payload = encrypt_configured_credentials({"access_token": "secret"})
        assert old_payload["key_version"] == 1

        configure_credential_vault(
            new_key,
            key_version=2,
            previous_keys={1: old_key},
        )
        assert decrypt_configured_credentials(old_payload) == {"access_token": "secret"}
        assert credential_rotation_required(old_payload) is True

        rotated = rotate_configured_credentials(old_payload)
        assert rotated["key_version"] == 2
        assert rotated["ciphertext"] != old_payload["ciphertext"]
        assert credential_rotation_required(rotated) is False
        assert decrypt_configured_credentials(rotated) == {"access_token": "secret"}
    finally:
        configure_credential_vault(TEST_APP_KEY, key_version=1)

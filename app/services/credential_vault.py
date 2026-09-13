"""Authenticated encryption for per-store integration credentials."""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.domain.errors import IntegrationNotConfiguredError

_ACTIVE_KEY_VERSION = 1
_KEYRING: dict[int, str] = {}
_LEGACY_KEYS: tuple[str, ...] = ()


def _fernet(secret_key: str) -> Fernet:
    digest = hashlib.sha256(secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def configure_credential_vault(
    secret_key: str,
    *,
    key_version: int = 1,
    previous_keys: dict[int, str] | None = None,
    legacy_keys: tuple[str, ...] = (),
) -> None:
    global _ACTIVE_KEY_VERSION, _KEYRING, _LEGACY_KEYS
    _ACTIVE_KEY_VERSION = key_version
    _KEYRING = {**(previous_keys or {}), key_version: secret_key}
    _LEGACY_KEYS = tuple(key for key in legacy_keys if key and key not in _KEYRING.values())


def encrypt_credentials(
    credentials: dict[str, str], secret_key: str, *, key_version: int = 1
) -> dict[str, Any]:
    payload = json.dumps(
        credentials, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return {
        "ciphertext": _fernet(secret_key).encrypt(payload).decode("ascii"),
        "key_version": key_version,
    }


def decrypt_credentials(payload: dict[str, Any], secret_key: str) -> dict[str, str]:
    ciphertext = payload.get("ciphertext")
    if not isinstance(ciphertext, str) or not ciphertext:
        return {}
    try:
        decoded = _fernet(secret_key).decrypt(ciphertext.encode("ascii"))
        raw = json.loads(decoded)
    except (InvalidToken, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise IntegrationNotConfiguredError(
            "Stored integration credentials cannot be decrypted"
        ) from exc
    if not isinstance(raw, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in raw.items()
    ):
        raise IntegrationNotConfiguredError("Stored integration credentials are invalid")
    return dict(raw)


def decrypt_configured_credentials(payload: dict[str, Any]) -> dict[str, str]:
    if not _KEYRING:
        raise IntegrationNotConfiguredError("Credential vault is not configured")
    version = payload.get("key_version")
    if isinstance(version, int) and version in _KEYRING:
        return decrypt_credentials(payload, _KEYRING[version])
    for key in (*_KEYRING.values(), *_LEGACY_KEYS):
        try:
            return decrypt_credentials(payload, key)
        except IntegrationNotConfiguredError:
            continue
    raise IntegrationNotConfiguredError("Stored integration credentials cannot be decrypted")


def encrypt_configured_credentials(credentials: dict[str, str]) -> dict[str, Any]:
    if not _KEYRING:
        raise IntegrationNotConfiguredError("Credential vault is not configured")
    return encrypt_credentials(
        credentials,
        _KEYRING[_ACTIVE_KEY_VERSION],
        key_version=_ACTIVE_KEY_VERSION,
    )


def credential_rotation_required(payload: dict[str, Any]) -> bool:
    return payload.get("key_version") != _ACTIVE_KEY_VERSION


def rotate_configured_credentials(payload: dict[str, Any]) -> dict[str, Any]:
    return encrypt_configured_credentials(decrypt_configured_credentials(payload))

"""Password hashing, signed sessions, and CSRF primitives for the single merchant MVP."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import struct
import time
from dataclasses import dataclass

from app.domain.errors import AuthenticationError

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    """Return a self-contained scrypt hash; plaintext is never stored."""

    actual_salt = salt or secrets.token_bytes(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=actual_salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=32,
    )
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${actual_salt.hex()}${derived.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt_hex, expected_hex = encoded.split("$", 5)
        if algorithm != "scrypt":
            return False
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(bytes.fromhex(expected_hex)),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual.hex(), expected_hex)


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def _encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


@dataclass(frozen=True)
class SessionClaims:
    session_id: str
    user_id: str
    email: str
    store_id: str
    csrf_token: str
    expires_at: int


def create_session_token(
    *,
    session_id: str,
    user_id: str,
    email: str,
    store_id: str,
    csrf_token: str,
    ttl_seconds: int,
    secret_key: str,
) -> str:
    payload = json.dumps(
        {
            "session_id": session_id,
            "user_id": user_id,
            "email": email,
            "store_id": store_id,
            "csrf_token": csrf_token,
            "expires_at": int(time.time()) + ttl_seconds,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    encoded = _encode(payload)
    signature = hmac.new(secret_key.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256)
    return f"{encoded}.{signature.hexdigest()}"


def decode_session_token(token: str, secret_key: str) -> SessionClaims:
    try:
        encoded, supplied_signature = token.split(".", 1)
        expected_signature = hmac.new(
            secret_key.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected_signature, supplied_signature):
            raise AuthenticationError()
        payload = json.loads(_decode(encoded))
        claims = SessionClaims(
            session_id=str(payload["session_id"]),
            user_id=str(payload["user_id"]),
            email=str(payload["email"]),
            store_id=str(payload["store_id"]),
            csrf_token=str(payload["csrf_token"]),
            expires_at=int(payload["expires_at"]),
        )
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        raise AuthenticationError() from exc
    if claims.expires_at < int(time.time()):
        raise AuthenticationError("Session expired")
    return claims


def hash_opaque_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_opaque_token() -> str:
    return secrets.token_urlsafe(48)


def create_signed_resource_token(
    resource: str,
    *,
    ttl_seconds: int,
    secret_key: str,
) -> str:
    payload = json.dumps(
        {
            "resource": resource,
            "expires_at": int(time.time()) + ttl_seconds,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    encoded = _encode(payload)
    signature = hmac.new(
        secret_key.encode(),
        encoded.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"{encoded}.{signature}"


def verify_signed_resource_token(
    token: str,
    resource: str,
    *,
    secret_key: str,
) -> bool:
    try:
        encoded, supplied_signature = token.split(".", 1)
        expected_signature = hmac.new(
            secret_key.encode(),
            encoded.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected_signature, supplied_signature):
            return False
        payload = json.loads(_decode(encoded))
        return (
            isinstance(payload, dict)
            and hmac.compare_digest(str(payload.get("resource", "")), resource)
            and int(payload.get("expires_at", 0)) >= int(time.time())
        )
    except (ValueError, TypeError, json.JSONDecodeError):
        return False


def new_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def totp_code(secret: str, *, timestamp: int | None = None) -> str:
    normalized = secret.strip().upper()
    key = base64.b32decode(normalized + "=" * (-len(normalized) % 8))
    counter = int(timestamp if timestamp is not None else time.time()) // 30
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = (struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF) % 1_000_000
    return f"{value:06d}"


def verify_totp(secret: str, code: str, *, timestamp: int | None = None) -> bool:
    if len(code) != 6 or not code.isdigit():
        return False
    now = timestamp if timestamp is not None else int(time.time())
    return any(
        hmac.compare_digest(totp_code(secret, timestamp=now + offset * 30), code)
        for offset in (-1, 0, 1)
    )

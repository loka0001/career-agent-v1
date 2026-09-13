"""Store API keys: generation, hashing, verification, and origin authorization.

The plaintext key is returned exactly once at creation; only its SHA-256 hash is
stored. Format: ``pk_<secret>`` for current keys; legacy ``ck_`` keys remain accepted.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ApiKeyModel
from app.domain.errors import AuthenticationError, NotFoundError

KEY_NAMESPACE = "pk_"
LEGACY_KEY_NAMESPACE = "ck_"
PREFIX_LENGTH = 8

WIDGET_SCOPE = "widget"
EVENTS_SCOPE = "events"
CATALOG_SCOPE = "catalog"
DEFAULT_SCOPES = [WIDGET_SCOPE, EVENTS_SCOPE, CATALOG_SCOPE]


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def create_api_key(
    session: Session,
    *,
    store_id: str,
    name: str,
    allowed_origins: list[str],
    scopes: list[str] | None = None,
) -> tuple[ApiKeyModel, str]:
    """Create a key; returns (row, plaintext). Plaintext is never stored."""

    normalized_origins = sorted({_normalize_origin(value) for value in allowed_origins})
    secret = secrets.token_urlsafe(24)
    raw_key = f"{KEY_NAMESPACE}{secret}"
    row = ApiKeyModel(
        store_id=store_id,
        name=name,
        key_prefix=raw_key[: len(KEY_NAMESPACE) + PREFIX_LENGTH],
        key_hash=_hash_key(raw_key),
        key_type="publishable",
        scopes_json=scopes or list(DEFAULT_SCOPES),
        allowed_origins_json=normalized_origins,
    )
    session.add(row)
    session.flush()
    return row, raw_key


def revoke_api_key(session: Session, *, store_id: str, key_id: int) -> ApiKeyModel:
    row = session.scalar(
        select(ApiKeyModel).where(ApiKeyModel.id == key_id, ApiKeyModel.store_id == store_id)
    )
    if row is None:
        raise NotFoundError(details={"entity": "api_key", "id": key_id})
    row.is_active = False
    row.revoked_at = datetime.now(UTC)
    session.flush()
    return row


def authenticate_api_key(session: Session, raw_key: str, *, scope: str) -> ApiKeyModel:
    """Resolve an active key with the required scope or raise AuthenticationError."""

    if not raw_key or not raw_key.startswith((KEY_NAMESPACE, LEGACY_KEY_NAMESPACE)):
        raise AuthenticationError("Invalid API key")
    row = session.scalar(select(ApiKeyModel).where(ApiKeyModel.key_hash == _hash_key(raw_key)))
    if row is None or not row.is_active:
        raise AuthenticationError("Invalid API key")
    if scope not in row.scopes_json:
        raise AuthenticationError("API key lacks the required scope")
    row.last_used_at = datetime.now(UTC)
    session.flush()
    return row


def _normalize_origin(origin: str) -> str:
    value = origin.strip().rstrip("/")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Allowed origins must be absolute HTTP(S) origins")
    if parsed.username or parsed.password or parsed.path not in {"", "/"}:
        raise ValueError("Allowed origins cannot contain credentials or paths")
    if parsed.query or parsed.fragment:
        raise ValueError("Allowed origins cannot contain query strings or fragments")
    host = parsed.hostname.casefold()
    if ":" in host:
        host = f"[{host}]"
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme.casefold()}://{host}{port}"


def origin_is_allowed(row: ApiKeyModel, origin: str | None) -> bool:
    if not origin or row.key_type != "publishable":
        return False
    try:
        normalized = _normalize_origin(origin)
    except (ValueError, TypeError):
        return False
    return normalized in set(row.allowed_origins_json or [])


def authorize_publishable_origin(
    session: Session,
    raw_key: str,
    origin: str | None,
    *,
    scope: str,
) -> ApiKeyModel:
    row = authenticate_api_key(session, raw_key, scope=scope)
    if not origin_is_allowed(row, origin):
        raise AuthenticationError("API key is not allowed on this origin")
    return row

"""Server-side account tokens, revocable sessions, lockout, and MFA lifecycle."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.models import AuthSessionModel, AuthTokenModel, UserModel
from app.domain.errors import AuthenticationError, InvalidInputError
from app.domain.models import AuthSessionOut
from app.integrations.email import EmailMessage, EmailSender
from app.security import hash_opaque_token, new_opaque_token

EMAIL_VERIFICATION = "email_verification"
PASSWORD_RESET = "password_reset"
TEAM_INVITE = "team_invite"


def aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def ensure_password_strength(password: str) -> None:
    categories = (
        any(character.islower() for character in password),
        any(character.isupper() for character in password),
        any(character.isdigit() for character in password),
        any(not character.isalnum() for character in password),
    )
    if len(password) < 10 or sum(categories) < 3:
        raise InvalidInputError(
            "Password needs at least 10 characters and three character categories",
            details={"field": "password", "requirement": "strong_password"},
        )


def create_auth_token(
    session: Session,
    *,
    purpose: str,
    email: str,
    user_id: str | None,
    organization_id: str | None = None,
    metadata: dict[str, str] | None = None,
    ttl: timedelta,
) -> tuple[AuthTokenModel, str]:
    now = datetime.now(UTC)
    session.execute(
        update(AuthTokenModel)
        .where(
            AuthTokenModel.email == email.casefold(),
            AuthTokenModel.purpose == purpose,
            AuthTokenModel.used_at.is_(None),
        )
        .values(used_at=now)
    )
    plaintext = new_opaque_token()
    row = AuthTokenModel(
        id=f"tok_{uuid.uuid4().hex[:20]}",
        user_id=user_id,
        organization_id=organization_id,
        purpose=purpose,
        token_hash=hash_opaque_token(plaintext),
        email=email.casefold(),
        metadata_json=metadata or {},
        expires_at=now + ttl,
    )
    session.add(row)
    session.flush()
    return row, plaintext


def consume_auth_token(session: Session, plaintext: str, purpose: str) -> AuthTokenModel:
    now = datetime.now(UTC)
    row = session.scalar(
        select(AuthTokenModel)
        .where(
            AuthTokenModel.token_hash == hash_opaque_token(plaintext),
            AuthTokenModel.purpose == purpose,
        )
        .with_for_update()
    )
    if row is None or row.used_at is not None or aware(row.expires_at) <= now:
        raise AuthenticationError(
            "Invalid or expired one-time token",
            details={"reason": "invalid_or_expired_token"},
        )
    row.used_at = now
    session.flush()
    return row


def deliver_action_email(
    sender: EmailSender,
    *,
    to: str,
    subject: str,
    text: str,
    public_base_url: str,
    route: str,
    token: str,
    idempotency_key: str,
) -> None:
    sender.send(
        EmailMessage(
            to=to,
            subject=subject,
            text=text,
            action_url=(f"{public_base_url.rstrip('/')}{route}?token={quote(token, safe='')}"),
            idempotency_key=idempotency_key,
        )
    )


def create_session(
    session: Session,
    *,
    user_id: str,
    store_id: str,
    csrf_token: str,
    ttl_seconds: int,
    user_agent: str,
    ip_address: str,
) -> AuthSessionModel:
    now = datetime.now(UTC)
    row = AuthSessionModel(
        id=f"ses_{uuid.uuid4().hex[:24]}",
        user_id=user_id,
        store_id=store_id,
        csrf_hash=hash_opaque_token(csrf_token),
        user_agent=user_agent[:500],
        ip_address=ip_address[:64],
        expires_at=now + timedelta(seconds=ttl_seconds),
        last_seen_at=now,
    )
    session.add(row)
    session.flush()
    return row


def validate_session(
    session: Session,
    *,
    session_id: str,
    user_id: str,
    store_id: str,
    csrf_token: str,
) -> AuthSessionModel:
    now = datetime.now(UTC)
    row = session.get(AuthSessionModel, session_id)
    if (
        row is None
        or row.user_id != user_id
        or row.store_id != store_id
        or row.revoked_at is not None
        or aware(row.expires_at) <= now
        or row.csrf_hash != hash_opaque_token(csrf_token)
    ):
        raise AuthenticationError("Session is no longer active")
    if aware(row.last_seen_at) < now - timedelta(minutes=5):
        row.last_seen_at = now
        session.flush()
    return row


def revoke_session(session: Session, session_id: str, user_id: str) -> bool:
    row = session.get(AuthSessionModel, session_id)
    if row is None or row.user_id != user_id:
        return False
    if row.revoked_at is None:
        row.revoked_at = datetime.now(UTC)
        session.flush()
    return True


def revoke_all_sessions(session: Session, user_id: str) -> None:
    session.execute(
        update(AuthSessionModel)
        .where(
            AuthSessionModel.user_id == user_id,
            AuthSessionModel.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )


def list_sessions(session: Session, user_id: str, current_session_id: str) -> list[AuthSessionOut]:
    rows = session.scalars(
        select(AuthSessionModel)
        .where(
            AuthSessionModel.user_id == user_id,
            AuthSessionModel.revoked_at.is_(None),
            AuthSessionModel.expires_at > datetime.now(UTC),
        )
        .order_by(AuthSessionModel.last_seen_at.desc())
    ).all()
    return [
        AuthSessionOut(
            session_id=row.id,
            current=row.id == current_session_id,
            user_agent=row.user_agent,
            ip_address=row.ip_address,
            created_at=row.created_at,
            last_seen_at=row.last_seen_at,
            expires_at=row.expires_at,
        )
        for row in rows
    ]


def reset_login_failures(user: UserModel) -> None:
    user.failed_login_count = 0
    user.locked_until = None


def record_login_failure(user: UserModel) -> None:
    user.failed_login_count += 1
    if user.failed_login_count < 2:
        user.locked_until = None
        return
    delay_seconds = min(2 ** (user.failed_login_count - 2), 60)
    user.locked_until = datetime.now(UTC) + timedelta(seconds=delay_seconds)

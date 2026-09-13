"""FastAPI dependencies for sessions, authentication, CSRF, and RBAC."""

from __future__ import annotations

import hmac
from collections.abc import Callable, Iterator
from typing import Annotated

from fastapi import Cookie, Depends, Header, Request
from sqlalchemy.orm import Session

from app.container import AppContainer
from app.domain.enums import MemberRole
from app.domain.errors import AuthenticationError, AuthorizationError
from app.domain.models import AuthUser
from app.repositories.tenant_repository import TenantRepository
from app.security import SessionClaims, decode_session_token
from app.services.auth_lifecycle import validate_session

SESSION_COOKIE = "commerce_session"
CSRF_COOKIE = "commerce_csrf"


def get_container(request: Request) -> AppContainer:
    return request.app.state.container  # type: ignore[no-any-return]


def get_db(container: Annotated[AppContainer, Depends(get_container)]) -> Iterator[Session]:
    session = container.session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session_claims(
    container: Annotated[AppContainer, Depends(get_container)],
    session_cookie: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> SessionClaims:
    if not session_cookie:
        raise AuthenticationError()
    return decode_session_token(session_cookie, container.settings.effective_secret_key)


def get_current_user(
    claims: Annotated[SessionClaims, Depends(get_session_claims)],
    db: Annotated[Session, Depends(get_db)],
) -> AuthUser:
    """Resolve access from the database on every request so revocation is immediate."""

    validate_session(
        db,
        session_id=claims.session_id,
        user_id=claims.user_id,
        store_id=claims.store_id,
        csrf_token=claims.csrf_token,
    )
    return TenantRepository(db).resolve_access(
        user_id=claims.user_id, store_id=claims.store_id
    )


def require_csrf(
    user: Annotated[AuthUser, Depends(get_current_user)],
    claims: Annotated[SessionClaims, Depends(get_session_claims)],
    header_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
    cookie_token: Annotated[str | None, Cookie(alias=CSRF_COOKIE)] = None,
) -> AuthUser:
    if (
        not header_token
        or not cookie_token
        or not hmac.compare_digest(header_token, claims.csrf_token)
        or not hmac.compare_digest(cookie_token, claims.csrf_token)
    ):
        raise AuthorizationError("Invalid CSRF token")
    return user


def require_min_role(minimum: MemberRole) -> Callable[[AuthUser], AuthUser]:
    """CSRF-protected dependency that also enforces a minimum tenant role."""

    def checker(user: Annotated[AuthUser, Depends(require_csrf)]) -> AuthUser:
        if not user.role.at_least(minimum):
            raise AuthorizationError(
                "Insufficient role for this action",
                details={"required": minimum.value, "role": user.role.value},
            )
        return user

    return checker


def require_min_role_read(minimum: MemberRole) -> Callable[[AuthUser], AuthUser]:
    """Role gate for safe methods; state-changing routes also require CSRF."""

    def checker(user: Annotated[AuthUser, Depends(get_current_user)]) -> AuthUser:
        if not user.role.at_least(minimum):
            raise AuthorizationError(
                "Insufficient role for this action",
                details={"required": minimum.value, "role": user.role.value},
            )
        return user

    return checker


def require_operator(
    user: Annotated[AuthUser, Depends(require_csrf)],
    container: Annotated[AppContainer, Depends(get_container)],
) -> AuthUser:
    allowed = {email.lower() for email in container.settings.operator_emails}
    if user.email.lower() not in allowed:
        raise AuthorizationError("Operator access is required")
    return user


def require_operator_read(
    user: Annotated[AuthUser, Depends(get_current_user)],
    container: Annotated[AppContainer, Depends(get_container)],
) -> AuthUser:
    allowed = {email.lower() for email in container.settings.operator_emails}
    if user.email.lower() not in allowed:
        raise AuthorizationError("Operator access is required")
    return user


ContainerDependency = Annotated[AppContainer, Depends(get_container)]
DatabaseDependency = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[AuthUser, Depends(get_current_user)]
CsrfUser = Annotated[AuthUser, Depends(require_csrf)]
AgentUser = Annotated[AuthUser, Depends(require_min_role(MemberRole.AGENT))]
MarketerUser = Annotated[AuthUser, Depends(require_min_role(MemberRole.MARKETER))]
AdminUser = Annotated[AuthUser, Depends(require_min_role(MemberRole.ADMIN))]
OwnerUser = Annotated[AuthUser, Depends(require_min_role(MemberRole.OWNER))]
AdminReadUser = Annotated[
    AuthUser, Depends(require_min_role_read(MemberRole.ADMIN))
]
OwnerReadUser = Annotated[
    AuthUser, Depends(require_min_role_read(MemberRole.OWNER))
]
SessionClaimsDependency = Annotated[SessionClaims, Depends(get_session_claims)]
OperatorUser = Annotated[AuthUser, Depends(require_operator)]
OperatorReadUser = Annotated[AuthUser, Depends(require_operator_read)]

"""Multi-tenant account lifecycle, revocable sessions, and MFA endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from fastapi import APIRouter, Request, Response, status
from sqlalchemy import select

from app.api.dependencies import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    ContainerDependency,
    CsrfUser,
    CurrentUser,
    DatabaseDependency,
    SessionClaimsDependency,
)
from app.api.schemas import (
    LoginResponse,
    MessageResponse,
    RegistrationResponse,
    StoreListResponse,
)
from app.config import Settings
from app.db.models import SubscriptionModel, UserModel
from app.domain.errors import (
    AccountLockedError,
    AuthenticationError,
    EmailNotVerifiedError,
    ExternalProviderError,
    IntegrationNotConfiguredError,
    MfaRequiredError,
)
from app.domain.models import (
    AcceptInviteInput,
    AuthSessionOut,
    AuthUser,
    ChangePasswordInput,
    DisableMfaInput,
    ForgotPasswordInput,
    LoginInput,
    MfaCodeInput,
    MfaSetupOut,
    RegisterInput,
    ResetPasswordInput,
    SwitchStoreInput,
    TokenInput,
)
from app.repositories.audit_repository import AuditRepository
from app.repositories.tenant_repository import TenantRepository
from app.security import (
    create_session_token,
    hash_password,
    new_csrf_token,
    new_totp_secret,
    verify_password,
    verify_totp,
)
from app.services.auth_lifecycle import (
    EMAIL_VERIFICATION,
    PASSWORD_RESET,
    aware,
    consume_auth_token,
    create_auth_token,
    create_session,
    deliver_action_email,
    ensure_password_strength,
    list_sessions,
    record_login_failure,
    reset_login_failures,
    revoke_all_sessions,
    revoke_session,
)
from app.services.billing import ensure_subscription
from app.services.credential_vault import (
    decrypt_configured_credentials,
    encrypt_configured_credentials,
)
from app.services.rate_limits import enforce_persistent_rate_limit, enforce_rate_limit
from app.services.team import accept_invite

router = APIRouter(prefix="/auth", tags=["auth"])

_DUMMY_PASSWORD_HASH = hash_password("invalid-credential-placeholder!", salt=b"auth-timing-salt")


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _clear_session(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")


def _issue_session(
    response: Response,
    settings: Settings,
    user: AuthUser,
    db: DatabaseDependency,
    request: Request,
) -> LoginResponse:
    csrf_token = new_csrf_token()
    row = create_session(
        db,
        user_id=user.user_id,
        store_id=user.store_id,
        csrf_token=csrf_token,
        ttl_seconds=settings.session_ttl_seconds,
        user_agent=request.headers.get("User-Agent", ""),
        ip_address=_client_ip(request),
    )
    session_token = create_session_token(
        session_id=row.id,
        user_id=user.user_id,
        email=user.email,
        store_id=user.store_id,
        csrf_token=csrf_token,
        ttl_seconds=settings.session_ttl_seconds,
        secret_key=settings.effective_secret_key,
    )
    secure_cookie = settings.cookie_secure or settings.app_env == "production"
    response.set_cookie(
        SESSION_COOKIE,
        session_token,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        max_age=settings.session_ttl_seconds,
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE,
        csrf_token,
        httponly=False,
        secure=secure_cookie,
        samesite="lax",
        max_age=settings.session_ttl_seconds,
        path="/",
    )
    return LoginResponse(
        user=user,
        csrf_token=csrf_token,
        is_operator=user.email.casefold()
        in {email.casefold() for email in settings.operator_emails},
        demo_mode=settings.demo_mode,
    )


def _ensure_access_policy(
    db: DatabaseDependency,
    *,
    settings: Settings,
    user: AuthUser,
) -> None:
    existing = db.scalar(
        select(SubscriptionModel).where(SubscriptionModel.organization_id == user.organization_id)
    )
    already_free = bool(
        existing is not None
        and existing.plan_key == "growth"
        and existing.status == "active"
        and existing.provider == "internal"
        and existing.trial_end is None
    )
    ensure_subscription(
        db,
        user.organization_id,
        free_access=settings.free_access_mode,
    )
    if settings.free_access_mode and not already_free:
        AuditRepository(db).add(
            actor=user.email,
            action="free_access_granted",
            entity_type="organization",
            entity_id=user.organization_id,
            metadata={
                "plan": "growth",
                "payment_required": False,
                "source": "FREE_ACCESS_MODE",
            },
            organization_id=user.organization_id,
            store_id=user.store_id,
            actor_user_id=user.user_id,
        )


@router.post(
    "/register",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an owner account and send a one-time verification link",
)
def register(
    payload: RegisterInput,
    request: Request,
    response: Response,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> RegistrationResponse:
    client_ip = _client_ip(request)
    enforce_rate_limit(db, f"register:{client_ip}", max_requests=5, window_seconds=3600)
    ensure_password_strength(payload.password)
    immediate_activation = container.settings.app_env == "test" or container.settings.demo_mode
    if not immediate_activation and not container.email_sender.available:
        raise IntegrationNotConfiguredError("Transactional email is required for registration")

    tenants = TenantRepository(db)
    user_row, _, store = tenants.create_tenant(
        organization_name=payload.organization_name,
        store_name=payload.store_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
    )
    if immediate_activation:
        user_row.email_verified_at = datetime.now(UTC)
    user = tenants.resolve_access(user_id=user_row.id, store_id=store.id)
    _ensure_access_policy(db, settings=container.settings, user=user)
    AuditRepository(db).add(
        actor=user.email,
        action="tenant_registered",
        entity_type="organization",
        entity_id=user.organization_id,
        metadata={"store_id": store.id},
        organization_id=user.organization_id,
        store_id=user.store_id,
        actor_user_id=user.user_id,
    )
    if immediate_activation:
        login = _issue_session(response, container.settings, user, db, request)
        return RegistrationResponse(
            verification_required=False,
            email=user.email,
            user=login.user,
            csrf_token=login.csrf_token,
        )

    token_row, plaintext = create_auth_token(
        db,
        purpose=EMAIL_VERIFICATION,
        email=user.email,
        user_id=user.user_id,
        ttl=timedelta(hours=24),
    )
    deliver_action_email(
        container.email_sender,
        to=user.email,
        subject="تأكيد حساب Commerce AI",
        text="أكد بريدك الإلكتروني لتفعيل حساب المتجر.",
        public_base_url=container.settings.public_base_url,
        route="/verify-email",
        token=plaintext,
        idempotency_key=f"verify-{token_row.id}",
    )
    return RegistrationResponse(verification_required=True, email=user.email)


@router.post("/verify-email", response_model=LoginResponse)
def verify_email(
    payload: TokenInput,
    request: Request,
    response: Response,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> LoginResponse:
    token = consume_auth_token(db, payload.token, EMAIL_VERIFICATION)
    if token.user_id is None:
        raise AuthenticationError("Verification token has no user")
    user_row = db.get(UserModel, token.user_id)
    if user_row is None or not user_row.is_active:
        raise AuthenticationError("Verification account is unavailable")
    user_row.email_verified_at = datetime.now(UTC)
    store = TenantRepository(db).default_store_for_user(user_row.id)
    user = TenantRepository(db).resolve_access(user_id=user_row.id, store_id=store.store_id)
    AuditRepository(db).add(
        actor=user.email,
        action="email_verified",
        entity_type="user",
        entity_id=user.user_id,
        organization_id=user.organization_id,
        store_id=user.store_id,
        actor_user_id=user.user_id,
    )
    return _issue_session(response, container.settings, user, db, request)


@router.post("/resend-verification", response_model=MessageResponse)
def resend_verification(
    payload: ForgotPasswordInput,
    request: Request,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> MessageResponse:
    enforce_rate_limit(
        db,
        f"verify-resend:{_client_ip(request)}:{payload.email.casefold()}",
        max_requests=3,
        window_seconds=3600,
    )
    user = TenantRepository(db).get_user_by_email(payload.email)
    if (
        user is not None
        and user.is_active
        and user.email_verified_at is None
        and container.email_sender.available
    ):
        token_row, plaintext = create_auth_token(
            db,
            purpose=EMAIL_VERIFICATION,
            email=user.email,
            user_id=user.id,
            ttl=timedelta(hours=24),
        )
        try:
            deliver_action_email(
                container.email_sender,
                to=user.email,
                subject="تأكيد حساب Commerce AI",
                text="استخدم الرابط الجديد لتأكيد بريدك الإلكتروني.",
                public_base_url=container.settings.public_base_url,
                route="/verify-email",
                token=plaintext,
                idempotency_key=f"verify-{token_row.id}",
            )
        except ExternalProviderError:
            token_row.used_at = datetime.now(UTC)
    return MessageResponse(message="verification_sent_if_account_exists")


@router.post("/login", response_model=LoginResponse, summary="Sign in securely")
def login(
    payload: LoginInput,
    request: Request,
    response: Response,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> LoginResponse:
    client_ip = _client_ip(request)
    enforce_persistent_rate_limit(
        container.session_factory,
        f"login-ip:{client_ip}",
        max_requests=30,
        window_seconds=60,
    )
    enforce_persistent_rate_limit(
        container.session_factory,
        f"login:{client_ip}:{payload.email.casefold()}",
        max_requests=10,
        window_seconds=60,
    )
    tenants = TenantRepository(db)
    user_row = tenants.get_user_by_email(payload.email)
    if user_row is None or not user_row.is_active:
        verify_password(payload.password, _DUMMY_PASSWORD_HASH)
        raise AuthenticationError("Invalid credentials")
    if user_row.locked_until is not None and aware(user_row.locked_until) > datetime.now(UTC):
        raise AccountLockedError(details={"retry_after": aware(user_row.locked_until).isoformat()})
    if not verify_password(payload.password, user_row.password_hash):
        record_login_failure(user_row)
        db.commit()
        raise AuthenticationError("Invalid credentials")
    if user_row.email_verified_at is None:
        raise EmailNotVerifiedError(details={"email": user_row.email})
    if user_row.mfa_enabled:
        credentials = decrypt_configured_credentials(user_row.mfa_secret_json)
        secret = credentials.get("secret", "")
        if payload.otp is None:
            raise MfaRequiredError()
        if not verify_totp(secret, payload.otp):
            record_login_failure(user_row)
            db.commit()
            raise AuthenticationError("Invalid verification code")
    reset_login_failures(user_row)
    default_store = tenants.default_store_for_user(user_row.id)
    user = tenants.resolve_access(user_id=user_row.id, store_id=default_store.store_id)
    _ensure_access_policy(db, settings=container.settings, user=user)
    AuditRepository(db).add(
        actor=user.email,
        action="signed_in",
        entity_type="user",
        entity_id=user.user_id,
        metadata={"ip": client_ip},
        organization_id=user.organization_id,
        store_id=user.store_id,
        actor_user_id=user.user_id,
    )
    return _issue_session(response, container.settings, user, db, request)


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    payload: ForgotPasswordInput,
    request: Request,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> MessageResponse:
    enforce_rate_limit(
        db,
        f"forgot:{_client_ip(request)}:{payload.email.casefold()}",
        max_requests=3,
        window_seconds=3600,
    )
    user = TenantRepository(db).get_user_by_email(payload.email)
    if user is not None and user.is_active and container.email_sender.available:
        token_row, plaintext = create_auth_token(
            db,
            purpose=PASSWORD_RESET,
            email=user.email,
            user_id=user.id,
            ttl=timedelta(hours=1),
        )
        try:
            deliver_action_email(
                container.email_sender,
                to=user.email,
                subject="إعادة تعيين كلمة مرور Commerce AI",
                text="طلبت إعادة تعيين كلمة المرور. تجاهل الرسالة إن لم تكن أنت.",
                public_base_url=container.settings.public_base_url,
                route="/reset-password",
                token=plaintext,
                idempotency_key=f"reset-{token_row.id}",
            )
        except ExternalProviderError:
            token_row.used_at = datetime.now(UTC)
    return MessageResponse(message="reset_sent_if_account_exists")


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    payload: ResetPasswordInput,
    db: DatabaseDependency,
) -> MessageResponse:
    ensure_password_strength(payload.password)
    token = consume_auth_token(db, payload.token, PASSWORD_RESET)
    if token.user_id is None:
        raise AuthenticationError("Reset token has no user")
    user = db.get(UserModel, token.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("Reset account is unavailable")
    user.password_hash = hash_password(payload.password)
    user.password_changed_at = datetime.now(UTC)
    user.email_verified_at = user.email_verified_at or datetime.now(UTC)
    reset_login_failures(user)
    revoke_all_sessions(db, user.id)
    AuditRepository(db).add(
        actor=user.email,
        action="password_reset",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=user.id,
    )
    return MessageResponse(message="password_reset")


@router.post("/accept-invite", response_model=LoginResponse)
def accept_team_invite(
    payload: AcceptInviteInput,
    request: Request,
    response: Response,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> LoginResponse:
    enforce_rate_limit(
        db,
        f"invite-accept:{_client_ip(request)}",
        max_requests=10,
        window_seconds=3600,
    )
    user = accept_invite(
        db,
        token=payload.token,
        password=payload.password,
        full_name=payload.full_name,
    )
    AuditRepository(db).add(
        actor=user.email,
        action="team_invite_accepted",
        entity_type="organization",
        entity_id=user.organization_id,
        metadata={"role": user.role.value},
        organization_id=user.organization_id,
        store_id=user.store_id,
        actor_user_id=user.user_id,
    )
    return _issue_session(response, container.settings, user, db, request)


@router.get("/me", response_model=LoginResponse)
def me(
    user: CurrentUser,
    claims: SessionClaimsDependency,
    container: ContainerDependency,
) -> LoginResponse:
    return LoginResponse(
        user=user,
        csrf_token=claims.csrf_token,
        is_operator=user.email.casefold()
        in {email.casefold() for email in container.settings.operator_emails},
        demo_mode=container.settings.demo_mode,
    )


@router.get("/stores", response_model=StoreListResponse, summary="Stores the user can access")
def stores(user: CurrentUser, db: DatabaseDependency) -> StoreListResponse:
    return StoreListResponse(stores=TenantRepository(db).stores_for_user(user.user_id))


@router.post("/switch-store", response_model=LoginResponse)
def switch_store(
    payload: SwitchStoreInput,
    request: Request,
    response: Response,
    user: CsrfUser,
    claims: SessionClaimsDependency,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> LoginResponse:
    target = TenantRepository(db).resolve_access(user_id=user.user_id, store_id=payload.store_id)
    revoke_session(db, claims.session_id, user.user_id)
    return _issue_session(response, container.settings, target, db, request)


@router.get("/sessions", response_model=list[AuthSessionOut])
def active_sessions(
    user: CurrentUser,
    claims: SessionClaimsDependency,
    db: DatabaseDependency,
) -> list[AuthSessionOut]:
    return list_sessions(db, user.user_id, claims.session_id)


@router.post("/sessions/{session_id}/revoke", response_model=MessageResponse)
def revoke_active_session(
    session_id: str,
    response: Response,
    user: CsrfUser,
    claims: SessionClaimsDependency,
    db: DatabaseDependency,
) -> MessageResponse:
    if not revoke_session(db, session_id, user.user_id):
        raise AuthenticationError("Session does not exist")
    if session_id == claims.session_id:
        _clear_session(response)
    return MessageResponse(message="session_revoked")


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordInput,
    response: Response,
    user: CsrfUser,
    db: DatabaseDependency,
) -> MessageResponse:
    ensure_password_strength(payload.new_password)
    row = db.get(UserModel, user.user_id)
    if row is None or not verify_password(payload.current_password, row.password_hash):
        raise AuthenticationError("Current password is incorrect")
    row.password_hash = hash_password(payload.new_password)
    row.password_changed_at = datetime.now(UTC)
    revoke_all_sessions(db, row.id)
    AuditRepository(db).add(
        actor=user.email,
        action="password_changed",
        entity_type="user",
        entity_id=user.user_id,
        organization_id=user.organization_id,
        store_id=user.store_id,
        actor_user_id=user.user_id,
    )
    _clear_session(response)
    return MessageResponse(message="password_changed")


@router.post("/mfa/setup", response_model=MfaSetupOut)
def setup_mfa(user: CsrfUser, db: DatabaseDependency) -> MfaSetupOut:
    row = db.get(UserModel, user.user_id)
    if row is None:
        raise AuthenticationError()
    secret = new_totp_secret()
    row.mfa_secret_json = encrypt_configured_credentials({"secret": secret})
    row.mfa_enabled = False
    issuer = quote("Commerce AI", safe="")
    label = quote(f"Commerce AI:{user.email}", safe="")
    return MfaSetupOut(
        secret=secret,
        otpauth_uri=f"otpauth://totp/{label}?secret={secret}&issuer={issuer}&digits=6&period=30",
    )


@router.post("/mfa/confirm", response_model=MessageResponse)
def confirm_mfa(
    payload: MfaCodeInput,
    user: CsrfUser,
    db: DatabaseDependency,
) -> MessageResponse:
    row = db.get(UserModel, user.user_id)
    if row is None or not row.mfa_secret_json:
        raise AuthenticationError("MFA setup has not started")
    secret = decrypt_configured_credentials(row.mfa_secret_json).get("secret", "")
    if not verify_totp(secret, payload.code):
        raise AuthenticationError("Invalid verification code")
    row.mfa_enabled = True
    AuditRepository(db).add(
        actor=user.email,
        action="mfa_enabled",
        entity_type="user",
        entity_id=user.user_id,
        organization_id=user.organization_id,
        store_id=user.store_id,
        actor_user_id=user.user_id,
    )
    return MessageResponse(message="mfa_enabled")


@router.post("/mfa/disable", response_model=MessageResponse)
def disable_mfa(
    payload: DisableMfaInput,
    response: Response,
    user: CsrfUser,
    db: DatabaseDependency,
) -> MessageResponse:
    row = db.get(UserModel, user.user_id)
    if row is None or not row.mfa_enabled:
        raise AuthenticationError("MFA is not enabled")
    secret = decrypt_configured_credentials(row.mfa_secret_json).get("secret", "")
    if not verify_password(payload.password, row.password_hash) or not verify_totp(
        secret, payload.code
    ):
        raise AuthenticationError("Password or verification code is incorrect")
    row.mfa_enabled = False
    row.mfa_secret_json = {}
    revoke_all_sessions(db, row.id)
    AuditRepository(db).add(
        actor=user.email,
        action="mfa_disabled",
        entity_type="user",
        entity_id=user.user_id,
        organization_id=user.organization_id,
        store_id=user.store_id,
        actor_user_id=user.user_id,
    )
    _clear_session(response)
    return MessageResponse(message="mfa_disabled")


@router.post("/logout", response_model=MessageResponse)
def logout(
    user: CsrfUser,
    claims: SessionClaimsDependency,
    response: Response,
    db: DatabaseDependency,
) -> MessageResponse:
    revoke_session(db, claims.session_id, user.user_id)
    _clear_session(response)
    return MessageResponse(message="signed_out")

"""Generated auth slice of models.py."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.domain.enums import MemberRole
from app.domain.model_groups.shared import ContractModel


class AuthUser(ContractModel):
    user_id: str
    email: str
    full_name: str = ""
    store_id: str
    organization_id: str
    role: MemberRole
    email_verified: bool = True
    mfa_enabled: bool = False


class StoreSummary(ContractModel):
    store_id: str
    name: str
    organization_id: str
    role: MemberRole


class LoginInput(ContractModel):
    email: str = Field(min_length=3, max_length=320, examples=["merchant@example.com"])
    password: str = Field(min_length=8, max_length=256, examples=["local-password"])
    otp: str | None = Field(default=None, pattern=r"^\d{6}$")


class RegisterInput(ContractModel):
    organization_name: str = Field(min_length=2, max_length=160)
    store_name: str = Field(min_length=2, max_length=160)
    email: str = Field(min_length=5, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=10, max_length=256)
    full_name: str = Field(default="", max_length=160)


class SwitchStoreInput(ContractModel):
    store_id: str = Field(min_length=1, max_length=64)


class TokenInput(ContractModel):
    token: str = Field(min_length=32, max_length=512)


class ForgotPasswordInput(ContractModel):
    email: str = Field(
        min_length=5,
        max_length=320,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )


class ResetPasswordInput(TokenInput):
    password: str = Field(min_length=10, max_length=256)


class AcceptInviteInput(TokenInput):
    password: str = Field(min_length=10, max_length=256)
    full_name: str = Field(default="", max_length=160)


class ChangePasswordInput(ContractModel):
    current_password: str = Field(min_length=8, max_length=256)
    new_password: str = Field(min_length=10, max_length=256)


class MfaCodeInput(ContractModel):
    code: str = Field(pattern=r"^\d{6}$")


class DisableMfaInput(MfaCodeInput):
    password: str = Field(min_length=8, max_length=256)


class AuthSessionOut(ContractModel):
    session_id: str
    current: bool
    user_agent: str
    ip_address: str
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime


class MfaSetupOut(ContractModel):
    secret: str
    otpauth_uri: str


class OnboardingStepOut(ContractModel):
    key: str
    title: str
    complete: bool
    required: bool
    href: str
    evidence: str


class OnboardingStatusOut(ContractModel):
    steps: list[OnboardingStepOut]
    completed_count: int
    required_count: int
    ready_to_activate: bool
    activated: bool


class SalesAssistInput(ContractModel):
    message: str = Field(
        min_length=1,
        max_length=2000,
        examples=["عايز سماعة للمذاكرة والمكالمات وميزانيتي 1500 جنيه"],
    )

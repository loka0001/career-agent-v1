"""Expected domain failures mapped to safe API responses."""

from __future__ import annotations

from typing import Any


class CommerceError(Exception):
    """Base expected error carrying a stable public code."""

    code = "commerce_error"
    http_status = 400
    public_message = "تعذر تنفيذ الطلب."

    def __init__(self, message: str | None = None, *, details: dict[str, Any] | None = None):
        super().__init__(message or self.public_message)
        self.details = details or {}


class InvalidInputError(CommerceError):
    code = "invalid_input"
    http_status = 400
    public_message = "البيانات المرسلة غير صالحة."


class AuthenticationError(CommerceError):
    code = "unauthenticated"
    http_status = 401
    public_message = "يجب تسجيل الدخول أولًا."


class MfaRequiredError(AuthenticationError):
    code = "mfa_required"
    public_message = "أدخل رمز التحقق من تطبيق المصادقة."


class AccountLockedError(CommerceError):
    code = "account_locked"
    http_status = 423
    public_message = "تم قفل الحساب مؤقتًا بعد محاولات دخول غير صحيحة."


class EmailNotVerifiedError(CommerceError):
    code = "email_not_verified"
    http_status = 403
    public_message = "يجب تأكيد البريد الإلكتروني قبل تسجيل الدخول."


class AuthorizationError(CommerceError):
    code = "forbidden"
    http_status = 403
    public_message = "غير مسموح بتنفيذ هذا الإجراء."


class NotFoundError(CommerceError):
    code = "not_found"
    http_status = 404
    public_message = "العنصر المطلوب غير موجود."


class ConflictError(CommerceError):
    code = "invalid_state"
    http_status = 409
    public_message = "لا يمكن تنفيذ الإجراء في الحالة الحالية."


class ContentNotApprovedError(ConflictError):
    code = "content_not_approved"
    public_message = "المحتوى يحتاج إلى موافقة قبل النشر."


class RateLimitedError(CommerceError):
    code = "rate_limited"
    http_status = 429
    public_message = "عدد الطلبات تجاوز الحد المسموح؛ حاول بعد قليل."


class QuotaExceededError(CommerceError):
    code = "quota_exceeded"
    http_status = 402
    public_message = "تم الوصول إلى حد الخطة الحالية."


class IntegrationNotConfiguredError(CommerceError):
    code = "integration_not_configured"
    http_status = 503
    public_message = "التكامل الخارجي غير مُعد حاليًا."


class ExternalProviderError(CommerceError):
    code = "external_provider_error"
    http_status = 502
    public_message = "تعذر الاتصال بالخدمة الخارجية."


class GroundingError(CommerceError):
    code = "grounding_failed"
    http_status = 502
    public_message = "تعذر إنشاء إجابة موثوقة من البيانات المتاحة."

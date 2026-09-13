from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.db.models import UserModel
from app.services.auth_lifecycle import record_login_failure, reset_login_failures


def test_login_failures_use_short_progressive_backoff_instead_of_hard_lock() -> None:
    user = UserModel(
        id="user-backoff",
        email="backoff@example.com",
        password_hash="unused",
        failed_login_count=0,
    )

    for _ in range(5):
        record_login_failure(user)

    assert user.failed_login_count == 5
    assert user.locked_until is not None
    assert user.locked_until <= datetime.now(UTC) + timedelta(seconds=9)

    reset_login_failures(user)
    assert user.failed_login_count == 0
    assert user.locked_until is None

from __future__ import annotations

import uuid

import pytest

from app.domain.errors import RateLimitedError
from app.services.rate_limits import enforce_rate_limit
from tests.conftest import TestContext


def test_database_rate_limit_is_shared_and_enforced(context: TestContext) -> None:
    key = f"integration:{uuid.uuid4().hex}"
    with context.session_factory.begin() as session:
        enforce_rate_limit(session, key, max_requests=2)
    with context.session_factory.begin() as session:
        enforce_rate_limit(session, key, max_requests=2)
    with pytest.raises(RateLimitedError), context.session_factory.begin() as session:
        enforce_rate_limit(session, key, max_requests=2)

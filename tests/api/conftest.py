from __future__ import annotations

import pytest
from sqlalchemy import delete

from app.db.models import RateLimitBucketModel
from tests.conftest import TestContext


@pytest.fixture(autouse=True)
def isolated_browser_session(context: TestContext):
    """API tests must not inherit authentication cookies from another test."""

    context.client.cookies.clear()
    with context.session_factory.begin() as session:
        session.execute(delete(RateLimitBucketModel))
    yield
    context.client.cookies.clear()

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.container import AppContainer, build_container
from app.db.base import Base
from app.db.models import RateLimitBucketModel
from app.db.seed import seed_database
from app.db.session import create_database_engine, create_session_factory
from app.integrations.email import RecordingEmailSender
from app.main import create_app
from app.security import hash_password

TEST_EMAIL = "merchant@example.com"
TEST_PASSWORD = "correct-horse-test-password"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"test-image-content"


@dataclass
class TestContext:
    __test__ = False

    client: TestClient
    container: AppContainer
    session_factory: sessionmaker[Session]

    def login(self) -> dict[str, str]:
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        )
        assert response.status_code == 200, response.text
        return {"X-CSRF-Token": str(response.json()["csrf_token"])}


@pytest.fixture(scope="session")
def context(tmp_path_factory: pytest.TempPathFactory) -> TestContext:
    root = tmp_path_factory.mktemp("commerce-ai-tests")
    settings = Settings(
        app_env="test",
        demo_mode=True,
        app_secret_key="test-secret-key-with-enough-entropy",
        database_url=f"sqlite:///{root / 'test.db'}",
        upload_directory=root / "uploads",
        chroma_directory=root / "chroma",
        public_base_url="http://testserver",
        allowed_origins=["http://testserver"],
        demo_merchant_email=TEST_EMAIL,
        demo_merchant_password_hash=hash_password(TEST_PASSWORD, salt=b"0123456789abcdef"),
        demo_store_id="demo-store",
        ai_provider="deterministic",
        image_storage_provider="local",
        enable_fake_publishing=True,
        enable_real_publishing=False,
        free_access_mode=False,
        billing_provider="demo",
        payment_provider="demo",
        enable_background_worker=False,
        max_image_bytes=1024,
    )
    engine = create_database_engine(settings.database_url)
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    container = build_container(settings, engine, factory)
    seed_database(settings, factory, container.vector_store)
    with TestClient(create_app(settings, container)) as client:
        yield TestContext(client=client, container=container, session_factory=factory)
    engine.dispose()


@pytest.fixture
def authenticated(context: TestContext) -> tuple[TestContext, dict[str, str]]:
    return context, context.login()


@pytest.fixture(autouse=True)
def isolated_request_state(context: TestContext):
    """Keep cookies and persistent rate-limit buckets isolated between tests."""

    context.client.cookies.clear()
    with context.session_factory.begin() as session:
        session.execute(delete(RateLimitBucketModel))
    yield
    context.client.cookies.clear()


def onboard_product(
    context: TestContext,
    headers: dict[str, str],
    product_id: str,
    *,
    price: str = "999.00",
    stock: str = "5",
) -> dict[str, object]:
    response = context.client.post(
        "/api/v1/products/onboard",
        headers=headers,
        data={
            "product_id": product_id,
            "name": f"Test Product {product_id}",
            "category": "Audio",
            "price": price,
            "stock": stock,
            "raw_features": '["Bluetooth", "microphone", "comfortable"]',
        },
        files={"image": ("product.png", PNG_BYTES, "image/png")},
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


def latest_email_token(context: TestContext, email: str) -> str:
    sender = context.container.email_sender
    assert isinstance(sender, RecordingEmailSender)
    message = next(item for item in reversed(sender.messages) if item.to == email.casefold())
    token = parse_qs(urlparse(message.action_url).query).get("token", [])
    assert token
    return token[0]

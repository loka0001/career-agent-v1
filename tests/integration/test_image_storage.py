from urllib.parse import urlparse

from app.integrations.image_storage import DatabaseImageStorage, LocalImageStorage
from tests.conftest import PNG_BYTES, TestContext


def test_database_image_storage_is_available_over_http(context: TestContext) -> None:
    storage = DatabaseImageStorage(
        context.session_factory,
        "http://testserver",
        context.container.settings.effective_secret_key,
    )

    stored = storage.store(PNG_BYTES, "image/png", store_id="demo-store")
    response = context.client.get(stored.original_url)

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert response.content == PNG_BYTES


def test_customer_media_requires_a_valid_temporary_signature(
    context: TestContext,
) -> None:
    storage = DatabaseImageStorage(
        context.session_factory,
        "http://testserver",
        context.container.settings.effective_secret_key,
    )
    stored = storage.store_media(PNG_BYTES, "image/png", store_id="demo-store")
    path, token = stored.original_url.split("?token=", 1)

    unsigned = context.client.get(path)
    valid = context.client.get(stored.original_url)
    tampered = context.client.get(f"{path}?token={token}x")

    assert unsigned.status_code == 404
    assert tampered.status_code == 404
    assert valid.status_code == 200
    assert valid.headers["cache-control"] == "private, no-store"
    assert valid.content == PNG_BYTES


def test_local_customer_media_is_not_exposed_by_the_public_upload_route(
    context: TestContext,
) -> None:
    storage = LocalImageStorage(
        context.container.settings.upload_directory,
        "http://testserver",
        context.container.settings.effective_secret_key,
    )
    stored = storage.store_media(PNG_BYTES, "image/png", store_id="demo-store")
    filename = urlparse(stored.original_url).path.rsplit("/", 1)[-1]

    bypass = context.client.get(f"/uploads/private/{filename}")
    signed = context.client.get(stored.original_url)

    assert bypass.status_code == 404
    assert signed.status_code == 200
    assert signed.headers["cache-control"] == "private, no-store"
    assert signed.content == PNG_BYTES

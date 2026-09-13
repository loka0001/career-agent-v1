from __future__ import annotations

import httpx
import pytest

from app.config import Settings
from app.domain.errors import ExternalProviderError
from app.integrations.facebook import _meta_error, request_with_network_retry
from app.integrations.instagram import RealInstagramPublisher


class PollingClient:
    def __init__(self) -> None:
        self.poll_count = 0

    def post(self, url: str, data: dict[str, str]) -> httpx.Response:
        del data
        assert url.endswith("/media")
        return httpx.Response(200, json={"id": "container-1"})

    def get(self, url: str, params: dict[str, str]) -> httpx.Response:
        del url, params
        self.poll_count += 1
        return httpx.Response(200, json={"status_code": "IN_PROGRESS"})

    def request(self, method: str, url: str, **kwargs: dict[str, str]) -> httpx.Response:
        if method == "POST":
            return self.post(url, kwargs.get("data", {}))
        return self.get(url, kwargs.get("params", {}))


class FlakyClient:
    def __init__(self) -> None:
        self.calls = 0

    def request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
        del method, url, kwargs
        self.calls += 1
        if self.calls == 1:
            raise httpx.ConnectError("temporary")
        return httpx.Response(200, json={"id": "ok"})


def test_meta_error_maps_token_failure_without_exposing_payload() -> None:
    response = httpx.Response(
        403,
        json={"error": {"code": 190, "message": "token-secret-value"}},
    )
    error = _meta_error(response)
    assert str(error) == "permission_or_token_error"
    assert error.details == {"provider_code": "190"}
    assert "token-secret-value" not in str(error.details)


def test_meta_network_failure_is_retried_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    delays: list[float] = []
    monkeypatch.setattr("app.integrations.facebook.time.sleep", delays.append)
    client = FlakyClient()
    response = request_with_network_retry(  # type: ignore[arg-type]
        client, "GET", "https://graph.facebook.com/example"
    )
    assert response.status_code == 200
    assert client.calls == 2
    assert delays == [0.2]


def test_non_idempotent_meta_post_transport_failure_is_never_retried() -> None:
    client = FlakyClient()

    with pytest.raises(ExternalProviderError, match="Meta network error"):
        request_with_network_retry(  # type: ignore[arg-type]
            client, "POST", "https://graph.facebook.com/example/photos"
        )

    assert client.calls == 1


def test_instagram_polling_is_bounded() -> None:
    settings = Settings(
        instagram_user_id="ig-user",
        instagram_access_token="secret",
        meta_poll_interval_seconds=0.001,
        meta_poll_timeout_seconds=0.005,
    )
    publisher = RealInstagramPublisher(settings)
    fake = PollingClient()
    publisher._client = fake  # type: ignore[assignment]
    result = publisher.publish("https://example.com/image.png", "caption")
    assert not result.success
    assert result.error_code == "container_not_ready"
    assert result.raw_status is not None and result.raw_status.startswith("TIMEOUT")
    assert 1 <= fake.poll_count < 20

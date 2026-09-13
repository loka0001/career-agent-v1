from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import TEST_EMAIL, TEST_PASSWORD, TestContext


def test_health_and_openapi_are_public(context: TestContext) -> None:
    assert context.client.get("/health/live").json()["status"] == "ok"
    ready = context.client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json()["checks"] == {
        "database": True,
        "search": True,
        "job_queue": True,
    }
    schema = context.client.get("/openapi.json").json()
    assert "/api/v1/products/onboard" in schema["paths"]


def test_authentication_and_csrf(context: TestContext) -> None:
    unauthorized = context.client.get("/api/v1/products")
    assert unauthorized.status_code == 401
    assert unauthorized.json()["error"]["code"] == "unauthenticated"
    bad_login = context.client.post(
        "/api/v1/auth/login", json={"email": TEST_EMAIL, "password": "wrong-password"}
    )
    assert bad_login.status_code == 401
    login = context.client.post(
        "/api/v1/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert login.status_code == 200
    assert login.json()["demo_mode"] is True
    assert "commerce_session" in login.headers["set-cookie"]
    me = context.client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["demo_mode"] is True
    forbidden = context.client.post("/api/v1/products/A101/activate")
    assert forbidden.status_code == 403
    csrf = login.json()["csrf_token"]
    logout = context.client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    assert logout.status_code == 200


def test_login_rate_limit_is_aggregated_by_client_ip(context: TestContext) -> None:
    responses = [
        context.client.post(
            "/api/v1/auth/login",
            json={"email": f"missing-{index}@example.com", "password": "wrong-password"},
        )
        for index in range(31)
    ]

    assert [response.status_code for response in responses[:30]] == [401] * 30
    assert responses[-1].status_code == 429


def test_request_id_and_security_headers(context: TestContext) -> None:
    response = context.client.get("/health/live", headers={"X-Request-ID": "known-request"})
    assert response.headers["X-Request-ID"] == "known-request"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
    assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin-allow-popups"


def test_production_headers_and_api_docs_are_restricted(context: TestContext) -> None:
    settings = context.container.settings.model_copy(deep=True)
    settings.app_env = "production"
    settings.cookie_secure = True
    with TestClient(create_app(settings, context.container)) as client:
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.headers["Strict-Transport-Security"].startswith("max-age=63072000")
        assert "upgrade-insecure-requests" in response.headers["Content-Security-Policy"]
        schema = client.get("/openapi.json")
        assert schema.status_code == 404
        assert schema.json()["error"]["code"] == "not_found"
        missing_api = client.get("/api/v1/conversations")
        assert missing_api.status_code == 404
        assert missing_api.json()["error"]["code"] == "not_found"
        assert missing_api.headers["Cache-Control"] == "no-store"

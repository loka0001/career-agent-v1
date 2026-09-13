"""Commerce AI FastAPI application factory."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api.error_handlers import install_error_handlers
from app.api.routes import (
    analytics,
    apikeys,
    auth,
    automations,
    billing,
    commerce,
    content,
    content_studio,
    customers,
    dashboard,
    health,
    inbox,
    integrations,
    meta_channels,
    operations,
    opportunities,
    orders,
    privacy,
    products,
    public,
    publishing,
    release,
    sales,
    team,
    whatsapp,
)
from app.api.routes import (
    settings as settings_routes,
)
from app.config import Settings, get_settings
from app.container import AppContainer, build_container
from app.db.models import MediaAssetModel
from app.db.session import create_database_engine, create_session_factory
from app.domain.errors import AuthenticationError
from app.logging_config import configure_logging
from app.request_tokens import bind_vercel_oidc_token, reset_vercel_oidc_token
from app.security import verify_signed_resource_token
from app.services.api_keys import (
    CATALOG_SCOPE,
    EVENTS_SCOPE,
    WIDGET_SCOPE,
    authorize_publishable_origin,
)

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, container: AppContainer | None = None) -> FastAPI:
    actual_settings = settings or get_settings()
    configure_logging()
    readiness_issues = actual_settings.production_readiness_issues()
    if readiness_issues:
        logger.warning(
            "production_capabilities_incomplete",
            extra={"missing_capabilities": readiness_issues},
        )
    sentry_dsn = actual_settings.sentry_dsn.get_secret_value()
    if sentry_dsn:
        import sentry_sdk

        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=actual_settings.app_env,
            release=actual_settings.release_sha or None,
            send_default_pii=False,
            traces_sample_rate=0.1,
            profiles_sample_rate=0.0,
        )
    if container is None:
        engine = create_database_engine(
            actual_settings.database_url,
            pool_size=actual_settings.database_pool_size,
            max_overflow=actual_settings.database_max_overflow,
            pool_recycle=actual_settings.database_pool_recycle_seconds,
        )
        container = build_container(actual_settings, engine, create_session_factory(engine))

    docs_enabled = actual_settings.app_env != "production"
    application = FastAPI(
        title="Commerce AI MVP",
        version="1.0.0",
        description="Arabic-first product publishing and grounded sales assistant.",
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )
    application.state.container = container
    application.add_middleware(
        CORSMiddleware,
        allow_origins=actual_settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "X-Api-Key",
            "X-CSRF-Token",
            "X-Client-Fingerprint",
            "Idempotency-Key",
        ],
    )

    def public_origin_allowed(request: Request) -> bool:
        path = request.url.path
        scope = (
            WIDGET_SCOPE
            if path.endswith("/chat")
            else EVENTS_SCOPE
            if path.endswith("/events")
            else CATALOG_SCOPE
            if path.endswith("/catalog")
            else None
        )
        origin = request.headers.get("origin")
        raw_key = request.query_params.get("key") or request.headers.get("x-api-key")
        if scope is None or not origin or not raw_key:
            return False
        session = container.session_factory()
        try:
            authorize_publishable_origin(session, raw_key, origin, scope=scope)
            return True
        except AuthenticationError:
            return False
        finally:
            session.rollback()
            session.close()

    @application.middleware("http")
    async def platform_request_credentials(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        token = bind_vercel_oidc_token(request.headers.get("x-vercel-oidc-token", ""))
        try:
            return await call_next(request)
        finally:
            reset_vercel_oidc_token(token)

    @application.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = request_id
        started = time.perf_counter()
        is_public_cors = request.url.path.startswith("/api/v1/public/")
        public_origin_ok = is_public_cors and public_origin_allowed(request)
        if is_public_cors and request.method == "OPTIONS":
            response = Response(status_code=204 if public_origin_ok else 403)
        else:
            response = await call_next(request)
        if public_origin_ok:
            response.headers["Access-Control-Allow-Origin"] = request.headers["origin"]
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = (
                "Content-Type, X-Api-Key, X-Client-Fingerprint"
            )
            response.headers["Access-Control-Max-Age"] = "600"
            response.headers.append("Vary", "Origin")
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
        csp = (
            "default-src 'self'; "
            "base-uri 'self'; "
            "object-src 'none'; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
            "script-src 'self' https://connect.facebook.net; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob: https:; "
            "media-src 'self' blob: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https://graph.facebook.com https://*.facebook.com; "
            "frame-src https://www.facebook.com https://web.facebook.com"
        )
        if actual_settings.app_env == "production":
            csp += "; upgrade-insecure-requests"
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )
        response.headers["Content-Security-Policy"] = csp
        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
        return response

    install_error_handlers(application)
    for router in (
        auth.router,
        automations.router,
        billing.router,
        commerce.router,
        products.router,
        content.router,
        content_studio.router,
        publishing.router,
        sales.router,
        settings_routes.router,
        team.router,
        integrations.router,
        meta_channels.router,
        orders.router,
        customers.router,
        opportunities.router,
        operations.router,
        privacy.router,
        dashboard.router,
        inbox.router,
        apikeys.router,
        analytics.router,
        public.router,
        release.router,
        whatsapp.router,
    ):
        application.include_router(router, prefix="/api/v1")
    application.include_router(whatsapp.webhook_router)
    application.include_router(commerce.webhook_router)
    application.include_router(commerce.oauth_callback_router)
    application.include_router(privacy.webhook_router)
    application.include_router(meta_channels.webhook_router)
    application.include_router(meta_channels.oauth_callback_router)
    application.include_router(billing.webhook_router)
    application.include_router(orders.webhook_router)
    application.include_router(orders.checkout_router)
    application.include_router(privacy.legal_router, prefix="/api/v1")
    application.include_router(health.router)

    if actual_settings.image_storage_provider == "local":
        actual_settings.upload_directory.mkdir(parents=True, exist_ok=True)

        @application.get("/uploads/{filename}", include_in_schema=False)
        def public_local_upload(filename: str) -> Response:
            if filename != Path(filename).name:
                return JSONResponse({"error": "not_found"}, status_code=404)
            path = actual_settings.upload_directory / filename
            if not path.is_file():
                return JSONResponse({"error": "not_found"}, status_code=404)
            return FileResponse(
                path,
                headers={
                    "Cache-Control": "public, max-age=31536000, immutable",
                    "X-Content-Type-Options": "nosniff",
                },
            )

    widget_path = Path(__file__).resolve().parent / "static" / "widget.js"

    @application.get("/widget.js", include_in_schema=False)
    def widget_script() -> Response:
        return FileResponse(
            widget_path,
            media_type="application/javascript",
            headers={"Cache-Control": "public, max-age=300"},
        )

    @application.get("/media/{asset_id}", include_in_schema=False)
    def media_asset(
        asset_id: str,
        token: str = Query(default=""),
    ) -> Response:
        with container.session_factory() as session:
            asset = session.get(MediaAssetModel, asset_id)
            if asset is None:
                return JSONResponse({"error": "not_found"}, status_code=404)
            if not asset.is_public and not verify_signed_resource_token(
                token,
                f"database-media:{asset_id}",
                secret_key=actual_settings.effective_secret_key,
            ):
                return JSONResponse({"error": "not_found"}, status_code=404)
            return Response(
                content=asset.content,
                media_type=asset.mime_type,
                headers={
                    "Cache-Control": (
                        "public, max-age=31536000, immutable"
                        if asset.is_public
                        else "private, no-store"
                    ),
                    "Content-Length": str(asset.byte_size),
                },
            )

    @application.get(
        "/private-media/{store_id}/{filename}",
        include_in_schema=False,
    )
    def private_local_media(
        store_id: str,
        filename: str,
        token: str = Query(default=""),
    ) -> Response:
        if filename != Path(filename).name or not verify_signed_resource_token(
            token,
            f"local-media:{store_id}:{filename}",
            secret_key=actual_settings.effective_secret_key,
        ):
            return JSONResponse({"error": "not_found"}, status_code=404)
        path = actual_settings.upload_directory / "private" / filename
        if not path.is_file():
            return JSONResponse({"error": "not_found"}, status_code=404)
        return FileResponse(
            path,
            headers={"Cache-Control": "private, no-store"},
        )

    project_root = Path(__file__).resolve().parent.parent
    web_dist = project_root / "web" / "dist"
    if not (web_dist / "index.html").exists():
        web_dist = project_root / "public"
    assets = web_dist / "assets"
    if assets.exists():
        application.mount("/assets", StaticFiles(directory=assets), name="web-assets")
    placeholders = web_dist / "placeholders"
    if placeholders.exists():
        application.mount("/placeholders", StaticFiles(directory=placeholders), name="placeholders")

    @application.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str, request: Request) -> Response:
        reserved_prefixes = (
            "api/",
            "health/",
            "webhooks/",
            "meta/oauth/",
            "checkout/",
            "media/",
            "private-media/",
            "uploads/",
        )
        if full_path == "openapi.json" or full_path.startswith(reserved_prefixes):
            return JSONResponse(
                {
                    "error": {
                        "code": "not_found",
                        "message": "Route not found.",
                        "details": {"path": request.url.path},
                        "request_id": str(getattr(request.state, "request_id", "unknown")),
                    }
                },
                status_code=404,
                headers={"Cache-Control": "no-store"},
            )
        index = web_dist / "index.html"
        if index.exists():
            return FileResponse(index)
        if actual_settings.app_env == "production":
            return HTMLResponse(
                '<!doctype html><html lang="en"><head><meta charset="utf-8">'
                "<title>Service unavailable</title></head><body>"
                "<main><h1>Frontend unavailable</h1>"
                "<p>The application frontend is not present in this release.</p></main>"
                "</body></html>",
                status_code=503,
                headers={"Cache-Control": "no-store"},
            )
        return JSONResponse({"name": "Commerce AI MVP", "docs": "/docs", "health": "/health/live"})

    return application


app = create_app()

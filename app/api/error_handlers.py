"""Safe and stable HTTP error envelopes."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.domain.errors import CommerceError

logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unknown"))


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(CommerceError)
    async def commerce_error_handler(request: Request, exc: CommerceError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.public_message,
                    "details": exc.details,
                    "request_id": _request_id(request),
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = {
            "fields": [
                {"location": list(error["loc"]), "message": error["msg"]} for error in exc.errors()
            ]
        }
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "schema_validation_error",
                    "message": "البيانات المرسلة لا تطابق الصيغة المطلوبة.",
                    "details": details,
                    "request_id": _request_id(request),
                }
            },
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_request_error", extra={"request_id": _request_id(request)})
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "حدث خطأ داخلي غير متوقع.",
                    "details": {},
                    "request_id": _request_id(request),
                }
            },
        )

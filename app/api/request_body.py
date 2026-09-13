"""Bounded request-body streaming for unauthenticated ingress routes."""

from __future__ import annotations

from fastapi import Request

from app.domain.errors import InvalidInputError


async def read_bounded_body(request: Request, *, max_bytes: int, label: str) -> bytes:
    declared_length = request.headers.get("content-length")
    if declared_length is not None:
        try:
            parsed_length = int(declared_length)
        except ValueError as exc:
            raise InvalidInputError(f"{label} Content-Length is invalid") from exc
        if parsed_length < 0 or parsed_length > max_bytes:
            raise InvalidInputError(f"{label} body is too large")

    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > max_bytes:
            raise InvalidInputError(f"{label} body is too large")
        body.extend(chunk)
    return bytes(body)

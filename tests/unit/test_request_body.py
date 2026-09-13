from __future__ import annotations

import asyncio

import pytest
from starlette.requests import Request

from app.api.request_body import read_bounded_body
from app.domain.errors import InvalidInputError


def _request(chunks: list[bytes], content_length: int | None = None) -> Request:
    messages = [
        {"type": "http.request", "body": chunk, "more_body": index < len(chunks) - 1}
        for index, chunk in enumerate(chunks)
    ]

    async def receive() -> dict[str, object]:
        return messages.pop(0)

    headers = [] if content_length is None else [(b"content-length", str(content_length).encode())]
    return Request({"type": "http", "method": "POST", "path": "/", "headers": headers}, receive)


def test_declared_oversized_body_is_rejected_before_stream_read() -> None:
    request = _request([b"unused"], content_length=11)

    with pytest.raises(InvalidInputError):
        asyncio.run(read_bounded_body(request, max_bytes=10, label="Webhook"))


def test_chunked_body_is_bounded_while_streaming() -> None:
    request = _request([b"12345", b"678901"])

    with pytest.raises(InvalidInputError):
        asyncio.run(read_bounded_body(request, max_bytes=10, label="Webhook"))


def test_bounded_body_preserves_valid_payload() -> None:
    request = _request([b"12345", b"67890"], content_length=10)

    body = asyncio.run(read_bounded_body(request, max_bytes=10, label="Webhook"))
    assert body == b"1234567890"

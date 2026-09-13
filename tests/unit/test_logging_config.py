"""Structured logging keeps diagnostics while redacting credentials."""

from __future__ import annotations

import json
import logging

from app.logging_config import JsonFormatter


def test_json_formatter_includes_redacted_exception() -> None:
    try:
        raise RuntimeError("password=super-secret")
    except RuntimeError:
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="request failed",
            args=(),
            exc_info=__import__("sys").exc_info(),
        )

    payload = json.loads(JsonFormatter().format(record))

    assert payload["message"] == "request failed"
    assert "RuntimeError" in payload["exception"]
    assert "super-secret" not in payload["exception"]
    assert "password=[REDACTED]" in payload["exception"]

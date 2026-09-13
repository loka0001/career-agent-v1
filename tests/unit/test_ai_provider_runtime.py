"""Production AI fail-closed behavior, usage capture, and circuit breaking."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest

from app.config import Settings
from app.domain.errors import ExternalProviderError, IntegrationNotConfiguredError
from app.domain.models import ImageAnalysis, ProductCreateInput
from app.integrations.ai_provider import (
    DisabledAIProvider,
    OpenAICompatibleProvider,
    build_ai_provider,
    consume_ai_metrics,
)
from app.request_tokens import bind_vercel_oidc_token, reset_vercel_oidc_token


class _Raw:
    usage_metadata: ClassVar[dict[str, int]] = {
        "input_tokens": 1000,
        "output_tokens": 500,
    }


class _Structured:
    def __init__(self, schema, *, fail: bool, calls: list[int]):
        self.schema = schema
        self.fail = fail
        self.calls = calls

    def invoke(self, messages):
        del messages
        self.calls.append(1)
        if self.fail:
            raise TimeoutError("provider timeout")
        return {
            "parsed": self.schema(
                customer_benefits=["Benefit"],
                description="Validated description",
            ),
            "raw": _Raw(),
            "parsing_error": None,
        }


class _FakeChatOpenAI:
    fail = False
    calls: ClassVar[list[int]] = []

    def __init__(self, **kwargs):
        del kwargs

    def with_structured_output(self, schema, **kwargs):
        assert kwargs["include_raw"] is True
        return _Structured(schema, fail=self.fail, calls=self.calls)


def _settings() -> Settings:
    return Settings(
        app_env="test",
        demo_mode=False,
        app_secret_key="test-secret-key-with-enough-entropy",
        database_url="sqlite://",
        ai_provider="openai",
        openai_api_key="test-openai-key",
        ai_circuit_failure_threshold=2,
        ai_circuit_open_seconds=60,
        ai_input_cost_per_million_usd="1.00",
        ai_output_cost_per_million_usd="2.00",
    )


def test_deterministic_provider_is_inaccessible_in_production() -> None:
    settings = Settings(
        app_env="test",
        demo_mode=False,
        app_secret_key="test-secret-key-with-enough-entropy",
        database_url="sqlite://",
        ai_provider="deterministic",
    )
    settings.app_env = "production"
    provider = build_ai_provider(settings, Path("app/prompts"))
    assert isinstance(provider, DisabledAIProvider)
    with pytest.raises(IntegrationNotConfiguredError):
        provider.extract_customer_need("hello", [])


def test_openai_usage_and_cost_are_captured(monkeypatch: pytest.MonkeyPatch) -> None:
    import langchain_openai

    _FakeChatOpenAI.fail = False
    _FakeChatOpenAI.calls = []
    monkeypatch.setattr(langchain_openai, "ChatOpenAI", _FakeChatOpenAI)
    provider = OpenAICompatibleProvider(_settings(), Path("app/prompts"))
    product = ProductCreateInput(
        product_id="ai-1",
        name="AI Product",
        category="Audio",
        price="100.00",
        stock=1,
        raw_features=["Bluetooth"],
    )
    provider.generate_product_copy(
        product,
        ImageAnalysis(
            product_type="Audio",
            image_summary="Merchant supplied image",
        ),
        ["Bluetooth"],
    )
    metrics = consume_ai_metrics(provider)
    assert metrics is not None
    assert metrics.input_tokens == 1000
    assert metrics.output_tokens == 500
    assert metrics.estimated_cost is not None
    assert str(metrics.estimated_cost) == "0.002"
    assert metrics.latency_ms >= 0


def test_vercel_gateway_metrics_identify_the_gateway(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import langchain_openai

    _FakeChatOpenAI.fail = False
    _FakeChatOpenAI.calls = []
    monkeypatch.setattr(langchain_openai, "ChatOpenAI", _FakeChatOpenAI)
    settings = _settings()
    settings.openai_api_key = type(settings.openai_api_key)("")
    settings.openai_base_url = "https://ai-gateway.vercel.sh/v1"
    settings.vercel_oidc_token = type(settings.vercel_oidc_token)("automatic-oidc")
    provider = OpenAICompatibleProvider(settings, Path("app/prompts"))
    product = ProductCreateInput(
        product_id="ai-gateway-1",
        name="AI Gateway Product",
        category="Audio",
        price="100.00",
        stock=1,
    )
    provider.generate_product_copy(
        product,
        ImageAnalysis(product_type="Audio", image_summary="Image"),
        [],
    )

    metrics = consume_ai_metrics(provider)

    assert metrics is not None
    assert metrics.provider == "vercel_ai_gateway"


def test_serverless_gateway_uses_request_scoped_oidc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import langchain_openai

    _FakeChatOpenAI.fail = False
    _FakeChatOpenAI.calls = []
    monkeypatch.setattr(langchain_openai, "ChatOpenAI", _FakeChatOpenAI)
    settings = Settings(
        app_env="test",
        demo_mode=False,
        app_secret_key="test-secret-key-with-enough-entropy",
        database_url="sqlite://",
        VERCEL=True,
        ai_provider="openai",
        openai_base_url="https://ai-gateway.vercel.sh/v1",
    )
    provider = OpenAICompatibleProvider(settings, Path("app/prompts"))
    product = ProductCreateInput(
        product_id="request-oidc",
        name="Request OIDC Product",
        category="Audio",
        price="100.00",
        stock=1,
    )
    context_token = bind_vercel_oidc_token("request-scoped-oidc")
    try:
        provider.generate_product_copy(
            product,
            ImageAnalysis(product_type="Audio", image_summary="Image"),
            [],
        )
    finally:
        reset_vercel_oidc_token(context_token)

    metrics = consume_ai_metrics(provider)
    assert metrics is not None
    assert metrics.provider == "vercel_ai_gateway"


def test_openai_circuit_opens_after_repeated_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import langchain_openai

    _FakeChatOpenAI.fail = True
    _FakeChatOpenAI.calls = []
    monkeypatch.setattr(langchain_openai, "ChatOpenAI", _FakeChatOpenAI)
    provider = OpenAICompatibleProvider(_settings(), Path("app/prompts"))
    product = ProductCreateInput(
        product_id="ai-2",
        name="AI Product",
        category="Audio",
        price="100.00",
        stock=1,
    )
    analysis = ImageAnalysis(product_type="Audio", image_summary="Image")
    for _ in range(3):
        with pytest.raises(ExternalProviderError):
            provider.generate_product_copy(product, analysis, [])
    assert len(_FakeChatOpenAI.calls) == 2

from __future__ import annotations

import json
from typing import Any

import pytest

from services.openrouter_agent_catalog import (
    OpenRouterAgentCatalogError,
    _StrictOpenRouterTransport,
    discover_free_openrouter_agent_configuration,
)
from services.runtime.ai_provider_adapter import ProviderEndpoint


class _Response:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def _model(model_id: str, *, free: bool, text: bool = True) -> dict[str, Any]:
    price = "0" if free else "0.000001"
    return {
        "id": model_id,
        "context_length": 65536,
        "pricing": {"prompt": price, "completion": price, "request": "0"},
        "architecture": {
            "input_modalities": ["text"] if text else ["image"],
            "output_modalities": ["text"],
        },
        "supported_parameters": ["max_tokens"],
        "top_provider": {"max_completion_tokens": 4096},
    }


def _completion() -> _Response:
    return _Response(
        {
            "id": "response-1",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": "bounded proposal"},
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 12},
        }
    )


def test_auto_catalog_prefers_direct_free_user_eligible_text_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "data": [
            _model("paid/model", free=False),
            _model("free/image-only", free=True, text=False),
            _model("free/text", free=True),
        ]
    }
    monkeypatch.setattr(
        "services.openrouter_agent_catalog.urllib.request.urlopen",
        lambda *_args, **_kwargs: _Response(payload),
    )
    configuration = discover_free_openrouter_agent_configuration(api_key="test-secret")
    assert configuration is not None
    selection = configuration.adapter.select("workflow.coordinate")
    assert selection.provider_id == "openrouter"
    assert selection.model_id == "free/text"
    assert configuration.configured_scopes == ()


def test_auto_catalog_uses_documented_free_router_when_no_direct_zero_price_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "services.openrouter_agent_catalog.urllib.request.urlopen",
        lambda *_args, **_kwargs: _Response(
            {
                "data": [
                    _model("paid/model", free=False),
                    _model("free/image-only", free=True, text=False),
                ]
            }
        ),
    )
    configuration = discover_free_openrouter_agent_configuration(api_key="test-secret")
    assert configuration is not None
    selection = configuration.adapter.select("workflow.coordinate")
    assert selection.provider_id == "openrouter"
    assert selection.model_id == "openrouter/free"


def test_strict_openrouter_transport_uses_only_provider_filterable_controls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def _urlopen(request: Any, *, timeout: float) -> _Response:
        captured["document"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return _completion()

    monkeypatch.setattr(
        "services.runtime.ai_provider_adapter.urllib.request.urlopen",
        _urlopen,
    )
    result = _StrictOpenRouterTransport().complete(
        ProviderEndpoint(
            "openrouter",
            "https://openrouter.ai/api/v1",
            "OPENROUTER_API_KEY",
        ),
        api_key="test-secret",
        model_id="openrouter/free",
        system_instructions="Return a bounded proposal.",
        prompt="Probe one capability.",
        max_output_tokens=128,
    )
    document = captured["document"]
    assert document["provider"] == {"require_parameters": True}
    assert document["max_tokens"] == 128
    assert "max_completion_tokens" not in document
    assert "modalities" not in document
    assert "reasoning" not in document
    assert result.output_tokens == 12


def test_strict_openrouter_transport_preserves_structured_output_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    response_format = {"type": "json_object"}

    def _urlopen(request: Any, *, timeout: float) -> _Response:
        captured["document"] = json.loads(request.data.decode("utf-8"))
        return _completion()

    monkeypatch.setattr(
        "services.runtime.ai_provider_adapter.urllib.request.urlopen",
        _urlopen,
    )
    _StrictOpenRouterTransport().complete(
        ProviderEndpoint(
            "openrouter",
            "https://openrouter.ai/api/v1",
            "OPENROUTER_API_KEY",
        ),
        api_key="test-secret",
        model_id="openrouter/free",
        system_instructions="Return JSON.",
        prompt="Verify evidence.",
        max_output_tokens=128,
        response_format=response_format,
    )
    document = captured["document"]
    assert document["provider"] == {"require_parameters": True}
    assert document["max_tokens"] == 128
    assert document["response_format"] == response_format
    assert "max_completion_tokens" not in document
    assert "modalities" not in document
    assert "reasoning" not in document


def test_strict_openrouter_transport_rejects_non_openrouter_endpoint() -> None:
    with pytest.raises(OpenRouterAgentCatalogError, match="non-OpenRouter"):
        _StrictOpenRouterTransport().complete(
            ProviderEndpoint(
                "local",
                "http://127.0.0.1:8080/v1",
                "LOCAL_KEY",
                requires_api_key=False,
            ),
            api_key="",
            model_id="local/model",
            system_instructions="Return text.",
            prompt="Probe.",
            max_output_tokens=64,
        )


def test_auto_catalog_rejects_malformed_catalog_instead_of_guessing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "services.openrouter_agent_catalog.urllib.request.urlopen",
        lambda *_args, **_kwargs: _Response({"unexpected": []}),
    )
    with pytest.raises(OpenRouterAgentCatalogError):
        discover_free_openrouter_agent_configuration(api_key="test-secret")


def test_auto_catalog_without_secret_is_disabled_without_network() -> None:
    assert discover_free_openrouter_agent_configuration(api_key="") is None

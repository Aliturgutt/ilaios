from __future__ import annotations

import json
from typing import Any

import pytest

from services.openrouter_agent_catalog import (
    OpenRouterAgentCatalogError,
    discover_free_openrouter_agent_configuration,
)


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

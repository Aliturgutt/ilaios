from __future__ import annotations

import json
from typing import Any

import pytest

from services.openrouter_agent_catalog import discover_free_openrouter_agent_configuration
from services.skill_engineering_runtime import SKILL_ENGINEERING_RUNTIME_BINDINGS


class _Response:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def test_openrouter_models_cover_exact_runtime_admitted_skill_capabilities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "data": [
            {
                "id": "free/text",
                "context_length": 65536,
                "pricing": {"prompt": "0", "completion": "0", "request": "0"},
                "architecture": {
                    "input_modalities": ["text"],
                    "output_modalities": ["text"],
                },
                "supported_parameters": ["max_tokens"],
                "top_provider": {"max_completion_tokens": 4096},
            }
        ]
    }
    monkeypatch.setattr(
        "services.openrouter_agent_catalog.urllib.request.urlopen",
        lambda *_args, **_kwargs: _Response(payload),
    )
    configuration = discover_free_openrouter_agent_configuration(api_key="test-secret")
    assert configuration is not None

    expected = {binding.capability for binding in SKILL_ENGINEERING_RUNTIME_BINDINGS}
    assert "test.execute" in expected
    assert expected <= configuration.provider_capabilities["openrouter"]
    for capability in sorted(expected):
        selection = configuration.adapter.select(capability)
        assert selection.provider_id == "openrouter"
        assert selection.model_id == "free/text"

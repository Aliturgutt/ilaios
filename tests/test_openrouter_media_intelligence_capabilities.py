from __future__ import annotations

import json
from typing import Any

import pytest

from services.ai_governance import GovernanceError
from services.media_intelligence_agent_execution import (
    MEDIA_INTELLIGENCE_GOVERNED_AI_CAPABILITIES,
)
from services.openrouter_agent_catalog import discover_free_openrouter_agent_configuration


class _Response:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def _free_text_model() -> dict[str, Any]:
    return {
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


def test_free_openrouter_bootstrap_covers_media_and_intelligence_proposals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "services.openrouter_agent_catalog.urllib.request.urlopen",
        lambda *_args, **_kwargs: _Response({"data": [_free_text_model()]}),
    )
    configuration = discover_free_openrouter_agent_configuration(api_key="test-secret")
    assert configuration is not None
    advertised = configuration.provider_capabilities["openrouter"]
    assert MEDIA_INTELLIGENCE_GOVERNED_AI_CAPABILITIES.issubset(advertised)
    for capability in MEDIA_INTELLIGENCE_GOVERNED_AI_CAPABILITIES:
        selection = configuration.adapter.select(capability)
        assert selection.provider_id == "openrouter"
        assert selection.model_id == "free/text"


def test_free_openrouter_never_gains_media_side_effect_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "services.openrouter_agent_catalog.urllib.request.urlopen",
        lambda *_args, **_kwargs: _Response({"data": [_free_text_model()]}),
    )
    configuration = discover_free_openrouter_agent_configuration(api_key="test-secret")
    assert configuration is not None
    advertised = configuration.provider_capabilities["openrouter"]
    for forbidden in ("provider.request", "media.write", "social.publish"):
        assert forbidden not in advertised
        with pytest.raises(GovernanceError):
            configuration.adapter.select(forbidden)

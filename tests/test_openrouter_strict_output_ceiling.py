from __future__ import annotations

import json
from typing import Any

import pytest

from services.openrouter_agent_catalog import _StrictOpenRouterTransport
from services.runtime.ai_provider_adapter import (
    AIProviderTransportError,
    ProviderEndpoint,
)


class _Response:
    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(
            {
                "id": "response-oversized",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": "bounded proposal"},
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 129},
            }
        ).encode("utf-8")


def test_strict_openrouter_output_ceiling_violation_is_retryable_provider_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _urlopen(request: Any, *, timeout: float) -> _Response:
        document = json.loads(request.data.decode("utf-8"))
        assert document["provider"] == {"require_parameters": True}
        assert document["max_tokens"] == 128
        return _Response()

    monkeypatch.setattr(
        "services.runtime.ai_provider_adapter.urllib.request.urlopen",
        _urlopen,
    )

    with pytest.raises(
        AIProviderTransportError,
        match="exceeded the required output-token ceiling",
    ) as captured:
        _StrictOpenRouterTransport().complete(
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

    assert captured.value.retryable is True

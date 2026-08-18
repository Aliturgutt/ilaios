from __future__ import annotations

import json
from typing import Any

import pytest

from services.runtime.ai_provider_adapter import (
    AIProviderTransportError,
    OpenAICompatibleTransport,
    ProviderEndpoint,
    _structured_response_format,
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


def _completion(
    content: object,
    *,
    finish_reason: str = "stop",
    error: object | None = None,
) -> _Response:
    choice: dict[str, Any] = {
        "finish_reason": finish_reason,
        "message": {"content": content},
    }
    if error is not None:
        choice["error"] = error
    return _Response(
        {
            "id": "response-1",
            "choices": [choice],
            "usage": {"prompt_tokens": 10, "completion_tokens": 12},
        }
    )


def test_independent_verifier_has_strict_json_schema_contract() -> None:
    response_format = _structured_response_format(
        "ilaios.skill.meta.independent-verification.v1"
    )
    assert response_format is not None
    assert response_format["type"] == "json_schema"
    json_schema = response_format["json_schema"]
    assert json_schema["strict"] is True
    schema = json_schema["schema"]
    assert schema["additionalProperties"] is False
    assert schema["required"] == [
        "verdict",
        "producer_evidence_digest",
        "findings",
    ]
    assert _structured_response_format("ilaios.skill.core.orchestration.v1") is None


def test_openai_transport_sends_structured_contract_and_requires_parameters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def _urlopen(request: Any, *, timeout: float) -> _Response:
        captured["document"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return _completion(
            json.dumps(
                {
                    "verdict": "PASS",
                    "producer_evidence_digest": "a" * 64,
                    "findings": [],
                }
            )
        )

    monkeypatch.setattr(
        "services.runtime.ai_provider_adapter.urllib.request.urlopen", _urlopen
    )
    response_format = _structured_response_format(
        "ilaios.skill.meta.independent-verification.v1"
    )
    assert response_format is not None
    result = OpenAICompatibleTransport().complete(
        ProviderEndpoint(
            "openrouter",
            "https://openrouter.ai/api/v1",
            "OPENROUTER_API_KEY",
            timeout_seconds=7.0,
        ),
        api_key="test-secret",
        model_id="openrouter/free",
        system_instructions="Return only the verdict document.",
        prompt="Verify this evidence.",
        max_output_tokens=128,
        response_format=response_format,
        require_parameters=True,
    )
    document = captured["document"]
    assert document["response_format"] == response_format
    assert document["provider"] == {"require_parameters": True}
    assert document["max_completion_tokens"] == 128
    assert document["modalities"] == ["text"]
    assert "max_tokens" not in document
    assert "reasoning" not in document
    assert result.response_id == "response-1"
    assert result.input_tokens == 10
    assert result.output_tokens == 12


def test_openrouter_normal_text_request_bounds_reasoning_and_output_modality(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def _urlopen(request: Any, *, timeout: float) -> _Response:
        captured["document"] = json.loads(request.data.decode("utf-8"))
        return _completion("bounded proposal")

    monkeypatch.setattr(
        "services.runtime.ai_provider_adapter.urllib.request.urlopen", _urlopen
    )
    result = OpenAICompatibleTransport().complete(
        ProviderEndpoint(
            "openrouter",
            "https://openrouter.ai/api/v1",
            "OPENROUTER_API_KEY",
        ),
        api_key="test-secret",
        model_id="example/free-model",
        system_instructions="Return a bounded proposal.",
        prompt="Probe one capability.",
        max_output_tokens=128,
    )
    document = captured["document"]
    assert document["max_completion_tokens"] == 128
    assert document["modalities"] == ["text"]
    assert "max_tokens" not in document
    assert document["reasoning"] == {
        "effort": "minimal",
        "exclude": True,
    }
    assert result.text == "bounded proposal"


def test_non_openrouter_endpoint_keeps_openai_compatible_max_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def _urlopen(request: Any, *, timeout: float) -> _Response:
        captured["document"] = json.loads(request.data.decode("utf-8"))
        return _completion("proposal")

    monkeypatch.setattr(
        "services.runtime.ai_provider_adapter.urllib.request.urlopen", _urlopen
    )
    OpenAICompatibleTransport().complete(
        ProviderEndpoint("local", "http://127.0.0.1:8080/v1", "LOCAL_KEY", requires_api_key=False),
        api_key="",
        model_id="local/model",
        system_instructions="Return text.",
        prompt="Probe.",
        max_output_tokens=64,
    )
    document = captured["document"]
    assert document["max_tokens"] == 64
    assert "max_completion_tokens" not in document
    assert "modalities" not in document
    assert "reasoning" not in document


def test_no_content_is_retryable_without_using_reasoning_as_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _urlopen(request: Any, *, timeout: float) -> _Response:
        return _completion(None, finish_reason="stop")

    monkeypatch.setattr(
        "services.runtime.ai_provider_adapter.urllib.request.urlopen", _urlopen
    )
    with pytest.raises(AIProviderTransportError, match="no text content") as captured:
        OpenAICompatibleTransport().complete(
            ProviderEndpoint(
                "openrouter",
                "https://openrouter.ai/api/v1",
                "OPENROUTER_API_KEY",
            ),
            api_key="test-secret",
            model_id="example/free-model",
            system_instructions="Return text.",
            prompt="Probe.",
            max_output_tokens=128,
        )
    assert captured.value.retryable is True


def test_length_exhaustion_without_text_is_classified_retryable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _urlopen(request: Any, *, timeout: float) -> _Response:
        return _completion(None, finish_reason="length")

    monkeypatch.setattr(
        "services.runtime.ai_provider_adapter.urllib.request.urlopen", _urlopen
    )
    with pytest.raises(AIProviderTransportError, match="exhausted completion budget") as captured:
        OpenAICompatibleTransport().complete(
            ProviderEndpoint(
                "openrouter",
                "https://openrouter.ai/api/v1",
                "OPENROUTER_API_KEY",
            ),
            api_key="test-secret",
            model_id="example/free-model",
            system_instructions="Return text.",
            prompt="Probe.",
            max_output_tokens=128,
        )
    assert captured.value.retryable is True


def test_in_body_provider_error_fails_closed_and_retryable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _urlopen(request: Any, *, timeout: float) -> _Response:
        return _completion(
            "partial output",
            finish_reason="error",
            error={"code": 502, "message": "provider unavailable"},
        )

    monkeypatch.setattr(
        "services.runtime.ai_provider_adapter.urllib.request.urlopen", _urlopen
    )
    with pytest.raises(AIProviderTransportError, match="in-body error") as captured:
        OpenAICompatibleTransport().complete(
            ProviderEndpoint(
                "openrouter",
                "https://openrouter.ai/api/v1",
                "OPENROUTER_API_KEY",
            ),
            api_key="test-secret",
            model_id="example/free-model",
            system_instructions="Return text.",
            prompt="Probe.",
            max_output_tokens=128,
        )
    assert captured.value.retryable is True


def test_non_text_completion_remains_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _urlopen(request: Any, *, timeout: float) -> _Response:
        return _completion([{"type": "text", "text": "not accepted here"}])

    monkeypatch.setattr(
        "services.runtime.ai_provider_adapter.urllib.request.urlopen", _urlopen
    )
    with pytest.raises(AIProviderTransportError, match="non-text completion"):
        OpenAICompatibleTransport().complete(
            ProviderEndpoint(
                "openrouter",
                "https://openrouter.ai/api/v1",
                "OPENROUTER_API_KEY",
            ),
            api_key="test-secret",
            model_id="example/free-model",
            system_instructions="Return text.",
            prompt="Probe.",
            max_output_tokens=128,
        )

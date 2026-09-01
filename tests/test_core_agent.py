"""Tests for src.core.agent (OpenRouterAgent).

All HTTP calls to OpenRouter are mocked; no live network requests are made.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.core.agent import (
    DEFAULT_MODEL,
    OpenRouterAgent,
    OpenRouterConfigError,
    OpenRouterResponseError,
)


def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)


def test_missing_api_key_raises_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    with pytest.raises(OpenRouterConfigError):
        OpenRouterAgent()


def test_default_model_is_claude_sonnet_5(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    agent = OpenRouterAgent()
    assert agent.model == DEFAULT_MODEL == "anthropic/claude-sonnet-5"


def test_openrouter_model_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "some/other-model")
    agent = OpenRouterAgent()
    assert agent.model == "some/other-model"


def _make_mock_response(
    json_body: dict[str, Any],
    status_code: int = 200,
    raise_error: Exception | None = None,
) -> MagicMock:
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = json_body
    if raise_error is not None:
        mock_response.raise_for_status.side_effect = raise_error
    else:
        mock_response.raise_for_status.return_value = None
    return mock_response


def test_chat_returns_message_content_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    agent = OpenRouterAgent()

    mock_response = _make_mock_response(
        {"choices": [{"message": {"content": "hello there"}}]}
    )

    with patch("src.core.agent.requests.post", return_value=mock_response) as mock_post:
        result = agent.chat("hi")

    assert result == "hello there"
    mock_post.assert_called_once()


def test_chat_raises_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    agent = OpenRouterAgent()

    http_error = requests.HTTPError("500 Server Error")
    mock_response = _make_mock_response({}, status_code=500, raise_error=http_error)

    with (
        patch("src.core.agent.requests.post", return_value=mock_response),
        pytest.raises(requests.HTTPError),
    ):
        agent.chat("hi")


def test_chat_raises_on_malformed_response(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    agent = OpenRouterAgent()

    mock_response = _make_mock_response({"unexpected": "shape"})

    with (
        patch("src.core.agent.requests.post", return_value=mock_response),
        pytest.raises(OpenRouterResponseError),
    ):
        agent.chat("hi")


def test_chat_sends_correct_authorization_header(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "secret-value")
    agent = OpenRouterAgent()

    mock_response = _make_mock_response(
        {"choices": [{"message": {"content": "ok"}}]}
    )

    with patch("src.core.agent.requests.post", return_value=mock_response) as mock_post:
        agent.chat("hi")

    _, kwargs = mock_post.call_args
    headers = kwargs["headers"]
    assert headers["Authorization"] == "Bearer secret-value"
    assert headers["Content-Type"] == "application/json"

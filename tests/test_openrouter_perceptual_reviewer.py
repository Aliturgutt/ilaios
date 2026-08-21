from __future__ import annotations

from collections.abc import Mapping
from email.message import Message
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError

import pytest

import src.video_automation.openrouter_perceptual_reviewer as reviewer_module
from src.video_automation.openrouter_perceptual_reviewer import (
    OpenRouterPerceptualReviewError,
    OpenRouterPerceptualReviewer,
    OpenRouterReviewResponse,
    UrllibOpenRouterReviewTransport,
)
from src.video_automation.perceptual_review import PerceptualReviewSubmission


class _QueuedTransport:
    def __init__(self, responses: list[OpenRouterReviewResponse]) -> None:
        self._responses = list(responses)
        self.requests: list[Mapping[str, object]] = []

    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, object],
        timeout_seconds: float,
    ) -> OpenRouterReviewResponse:
        del url, headers, timeout_seconds
        self.requests.append(body)
        if not self._responses:
            raise AssertionError("unexpected OpenRouter review request")
        return self._responses.pop(0)


class _UrlopenResponse:
    status = 200

    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self) -> _UrlopenResponse:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        del exc_type, exc, traceback

    def read(self) -> bytes:
        return self._payload


def _retry_after_headers(value: str) -> Message:
    headers = Message()
    headers["Retry-After"] = value
    return headers


def _success_payload(
    *,
    score: float = 0.91,
    detail: str = "The sampled frames match the requested scene.",
    repair_target: str = "",
) -> dict[str, object]:
    return {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"score":'
                        f"{score}"
                        ',"detail":'
                        f'"{detail}"'
                        ',"repair_target":'
                        f'"{repair_target}"'
                        "}"
                    )
                }
            }
        ]
    }


def _review(
    transport: _QueuedTransport,
    monkeypatch: pytest.MonkeyPatch,
) -> PerceptualReviewSubmission:
    monkeypatch.setattr(
        reviewer_module,
        "_sample_frames",
        lambda path, count: (b"frame-one", b"frame-two"),
    )
    reviewer = OpenRouterPerceptualReviewer(
        "secret",
        "openrouter/free",
        sample_count=2,
        transport=transport,
    )
    return reviewer.review(
        video_path=Path("unused.mp4"),
        objective="Create a cinematic coastal city video.",
        artifact_sha256="a" * 64,
        producer_id="provider-video:seedance",
        review_id="review-1",
    )


def test_perceptual_reviewer_prefers_strict_json_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _QueuedTransport([OpenRouterReviewResponse(200, _success_payload())])

    submission = _review(transport, monkeypatch)

    assert len(transport.requests) == 1
    response_format = transport.requests[0]["response_format"]
    assert isinstance(response_format, Mapping)
    assert response_format["type"] == "json_schema"
    provider = transport.requests[0]["provider"]
    assert isinstance(provider, Mapping)
    assert provider["require_parameters"] is True
    assert submission.score == pytest.approx(0.91)
    assert "route=json-schema" in submission.provenance_reference


def _assert_capability_fallback(
    status_code: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _QueuedTransport(
        [
            OpenRouterReviewResponse(
                status_code,
                {"error": {"code": status_code, "message": "No route available"}},
            ),
            OpenRouterReviewResponse(200, _success_payload()),
        ]
    )

    submission = _review(transport, monkeypatch)

    assert len(transport.requests) == 2
    first_format = transport.requests[0]["response_format"]
    assert isinstance(first_format, Mapping)
    assert first_format["type"] == "json_schema"
    assert "response_format" not in transport.requests[1]
    assert transport.requests[1]["model"] == "openrouter/free"
    provider = transport.requests[1]["provider"]
    assert isinstance(provider, Mapping)
    assert provider["require_parameters"] is True
    assert submission.score == pytest.approx(0.91)
    assert "route=prompt-json-fallback" in submission.provenance_reference


def test_perceptual_reviewer_falls_back_on_404(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _assert_capability_fallback(404, monkeypatch)


def test_perceptual_reviewer_fails_closed_when_stale_model_404_persists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _QueuedTransport(
        [
            OpenRouterReviewResponse(
                404,
                {"error": {"code": 404, "message": "model not found"}},
            ),
            OpenRouterReviewResponse(
                404,
                {"error": {"code": 404, "message": "model not found"}},
            ),
        ]
    )

    with pytest.raises(OpenRouterPerceptualReviewError, match="HTTP 404"):
        _review(transport, monkeypatch)

    assert len(transport.requests) == 2
    assert "response_format" in transport.requests[0]
    assert "response_format" not in transport.requests[1]


def test_perceptual_reviewer_falls_back_on_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _assert_capability_fallback(503, monkeypatch)


def test_perceptual_reviewer_does_not_retry_non_capability_http_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _QueuedTransport(
        [
            OpenRouterReviewResponse(
                400,
                {"error": {"code": 400, "message": "Bad request"}},
            )
        ]
    )

    with pytest.raises(OpenRouterPerceptualReviewError, match="HTTP 400"):
        _review(transport, monkeypatch)

    assert len(transport.requests) == 1


def test_perceptual_reviewer_fallback_remains_fail_closed_on_extra_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _success_payload()
    choices = payload["choices"]
    assert isinstance(choices, list)
    first = choices[0]
    assert isinstance(first, dict)
    message = first["message"]
    assert isinstance(message, dict)
    message["content"] = (
        '{"score":0.91,"detail":"match","repair_target":"","unexpected":"value"}'
    )
    transport = _QueuedTransport(
        [
            OpenRouterReviewResponse(
                404,
                {"error": {"code": 404, "message": "No route available"}},
            ),
            OpenRouterReviewResponse(200, payload),
        ]
    )

    with pytest.raises(OpenRouterPerceptualReviewError, match="contain exactly"):
        _review(transport, monkeypatch)

    assert len(transport.requests) == 2


def test_transport_retries_429_once_when_retry_after_is_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0
    sleeps: list[float] = []

    def fake_urlopen(request: object, *, timeout: float) -> _UrlopenResponse:
        nonlocal calls
        del request, timeout
        calls += 1
        if calls == 1:
            raise HTTPError(
                "https://openrouter.ai/api/v1/chat/completions",
                429,
                "rate limited",
                _retry_after_headers("0"),
                BytesIO(b'{"error":{"code":429,"message":"rate limited"}}'),
            )
        return _UrlopenResponse(b'{"choices":[]}')

    monkeypatch.setattr(reviewer_module, "urlopen", fake_urlopen)
    monkeypatch.setattr(reviewer_module, "sleep", sleeps.append)

    response = UrllibOpenRouterReviewTransport().post_json(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": "Bearer secret"},
        body={"model": "openrouter/free"},
        timeout_seconds=5.0,
    )

    assert response.status_code == 200
    assert calls == 2
    assert sleeps == [0.0]


def test_transport_persistent_429_retries_only_once_then_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0
    sleeps: list[float] = []

    def fake_urlopen(request: object, *, timeout: float) -> _UrlopenResponse:
        nonlocal calls
        del request, timeout
        calls += 1
        raise HTTPError(
            "https://openrouter.ai/api/v1/chat/completions",
            429,
            "rate limited",
            _retry_after_headers("0"),
            BytesIO(b'{"error":{"code":429,"message":"rate limited"}}'),
        )

    monkeypatch.setattr(reviewer_module, "urlopen", fake_urlopen)
    monkeypatch.setattr(reviewer_module, "sleep", sleeps.append)

    response = UrllibOpenRouterReviewTransport().post_json(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": "Bearer secret"},
        body={"model": "openrouter/free"},
        timeout_seconds=5.0,
    )

    assert response.status_code == 429
    assert calls == 2
    assert sleeps == [0.0]


def test_transport_429_without_bounded_retry_after_fails_closed_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0
    sleeps: list[float] = []

    def fake_urlopen(request: object, *, timeout: float) -> _UrlopenResponse:
        nonlocal calls
        del request, timeout
        calls += 1
        raise HTTPError(
            "https://openrouter.ai/api/v1/chat/completions",
            429,
            "rate limited",
            _retry_after_headers("120"),
            BytesIO(b'{"error":{"code":429,"message":"rate limited"}}'),
        )

    monkeypatch.setattr(reviewer_module, "urlopen", fake_urlopen)
    monkeypatch.setattr(reviewer_module, "sleep", sleeps.append)

    response = UrllibOpenRouterReviewTransport().post_json(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": "Bearer secret"},
        body={"model": "openrouter/free"},
        timeout_seconds=5.0,
    )

    assert response.status_code == 429
    assert calls == 1
    assert sleeps == []

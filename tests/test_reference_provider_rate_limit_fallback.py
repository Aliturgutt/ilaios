from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import pytest

from services.integrations.reference_aware_provider_video_runtime import (
    ReferenceAwareProviderBackedDesktopVideoRuntime,
    _native_reference_metadata_fallback,
)
from services.integrations.video_runtime import VideoRuntimeError
from src.video_automation.reference_image_analysis import (
    ReferenceImageAnalysisError,
    ReferenceImageInput,
)


@dataclass(frozen=True)
class _Role:
    value: str


@dataclass(frozen=True)
class _Record:
    sha256: str
    mime_type: str
    role: _Role
    instruction: str | None
    content: bytes


class _ReferenceStore:
    def __init__(self, records: tuple[_Record, ...]) -> None:
        self._records = records

    def for_request(self, request_id: str) -> tuple[_Record, ...]:
        assert request_id == "req-1"
        return self._records

    def read_bytes(self, record: _Record) -> bytes:
        return record.content


class _Cache:
    def __init__(self) -> None:
        self.put_calls: list[dict[str, object]] = []

    def get(self, request_id: str) -> None:
        assert request_id == "req-1"
        return None

    def put(
        self,
        *,
        request_id: str,
        text: str,
        reference_sha256s: tuple[str, ...],
        analyzer_id: str,
    ) -> object:
        self.put_calls.append(
            {
                "request_id": request_id,
                "text": text,
                "reference_sha256s": reference_sha256s,
                "analyzer_id": analyzer_id,
            }
        )
        return type(
            "FrozenBrief",
            (),
            {
                "text": text,
                "reference_sha256s": reference_sha256s,
                "analyzer_id": analyzer_id,
            },
        )()


class _FailingAnalyzer:
    def __init__(self, message: str) -> None:
        self._message = message

    def analyze(self, references: tuple[ReferenceImageInput, ...]) -> object:
        assert references
        raise ReferenceImageAnalysisError(self._message)


def _runtime_with_analyzer(message: str) -> ReferenceAwareProviderBackedDesktopVideoRuntime:
    content = b"reference-image"
    digest = hashlib.sha256(content).hexdigest()
    record = _Record(
        sha256=digest,
        mime_type="image/png",
        role=_Role("product"),
        instruction="Preserve the admitted product reference.",
        content=content,
    )
    runtime = object.__new__(ReferenceAwareProviderBackedDesktopVideoRuntime)
    runtime_injected: Any = runtime
    runtime_injected._reference_assets = _ReferenceStore((record,))
    runtime_injected._reference_brief_cache = _Cache()
    runtime_injected._reference_analyzer = _FailingAnalyzer(message)
    return runtime


def test_metadata_fallback_preserves_digest_identity_without_inventing_visual_facts() -> None:
    content = b"image"
    digest = hashlib.sha256(content).hexdigest()
    reference = ReferenceImageInput(
        content=content,
        mime_type="image/png",
        sha256_hex=digest,
        role="product",
        instruction="Preserve the product.",
    )

    brief = _native_reference_metadata_fallback((reference,))

    assert brief.reference_sha256s == (digest,)
    assert brief.analyzer_id == "native-reference-metadata-fallback:v1"
    assert "supplied directly" in brief.text
    assert "no inferred visual description" in brief.text


def test_reference_brief_uses_metadata_fallback_for_rate_limit_only() -> None:
    runtime = _runtime_with_analyzer("reference image analysis failed with HTTP 429")

    brief = runtime._reference_brief("req-1")

    assert brief is not None
    assert brief.analyzer_id == "native-reference-metadata-fallback:v1"
    runtime_injected: Any = runtime
    assert runtime_injected._reference_brief_cache.put_calls


def test_reference_brief_remains_fail_closed_for_non_transient_analyzer_errors() -> None:
    runtime = _runtime_with_analyzer("reference image analysis content is invalid JSON")

    with pytest.raises(VideoRuntimeError, match="reference image conditioning failed"):
        runtime._reference_brief("req-1")

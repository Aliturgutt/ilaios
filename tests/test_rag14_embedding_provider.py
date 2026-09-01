"""Fail-closed tests for the RAG.14 pinned production embedding provider."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

import pytest

from services.rag14_embedding_certification import load_candidate
from services.rag14_embedding_provider import (
    PRODUCTION_EMBEDDING_MODE,
    VERIFICATION_EMBEDDING_MODE,
    PinnedE5EmbeddingProvider,
    ProductionEmbeddingError,
    embedding_provider_from_environment,
    query_embedding_context,
)


_REPOSITORY = Path(__file__).resolve().parents[1]
_MANIFEST = _REPOSITORY / "infra/rag/multilingual-e5-small-qint8.candidate.json"
_PROVIDER_SOURCE = _REPOSITORY / "services/rag14_embedding_provider.py"


def _provider_without_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[PinnedE5EmbeddingProvider, list[tuple[str, ...]]]:
    provider_any: Any = object.__new__(PinnedE5EmbeddingProvider)
    provider_any._candidate = load_candidate(_MANIFEST)
    captured: list[tuple[str, ...]] = []

    def fake_encode(texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        captured.append(tuple(texts))
        dimensions = int(provider_any._candidate.embedding_dimensions)
        return (tuple(0.0 for _ in range(dimensions)),)

    monkeypatch.setattr(provider_any, "_encode", fake_encode)
    return cast(PinnedE5EmbeddingProvider, provider_any), captured


def test_query_and_passage_prefixes_are_context_local_and_restored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, captured = _provider_without_runtime(monkeypatch)

    provider.embed("tenant isolation")
    with query_embedding_context():
        provider.embed("tenant isolation")
    provider.embed("tenant isolation")

    assert captured[0] == ("passage: tenant isolation",)
    assert captured[1] == ("query: tenant isolation",)
    assert captured[2] == ("passage: tenant isolation",)


def test_candidate_identity_drift_fails_before_runtime_loading(tmp_path: Path) -> None:
    payload = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    payload["upstream_revision"] = "0" * 40
    manifest = tmp_path / "candidate.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ProductionEmbeddingError, match="revision drifted"):
        PinnedE5EmbeddingProvider(manifest_path=manifest, artifact_root=tmp_path)


def test_tampered_model_artifact_fails_before_runtime_loading(tmp_path: Path) -> None:
    candidate = load_candidate(_MANIFEST)
    for artifact in candidate.artifacts:
        path = tmp_path / artifact.path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"tampered")

    with pytest.raises(ProductionEmbeddingError, match="artifact SHA mismatch"):
        PinnedE5EmbeddingProvider(manifest_path=_MANIFEST, artifact_root=tmp_path)


def test_embedding_mode_resolution_is_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ILAIOS_KNOWLEDGE_EMBEDDING_MODE", raising=False)
    assert embedding_provider_from_environment() is None

    monkeypatch.setenv(
        "ILAIOS_KNOWLEDGE_EMBEDDING_MODE", VERIFICATION_EMBEDDING_MODE
    )
    assert embedding_provider_from_environment() is None

    monkeypatch.setenv("ILAIOS_KNOWLEDGE_EMBEDDING_MODE", "unknown-provider")
    with pytest.raises(ProductionEmbeddingError, match="unknown"):
        embedding_provider_from_environment()

    assert PRODUCTION_EMBEDDING_MODE == "multilingual_e5_small_qint8_v1"


def test_provider_has_no_runtime_network_fetch_and_matches_certified_session_policy() -> None:
    source = _PROVIDER_SOURCE.read_text(encoding="utf-8")

    assert "urllib" not in source
    assert "requests" not in source
    assert "huggingface_hub" not in source
    assert "options.intra_op_num_threads = 1" in source
    assert "options.inter_op_num_threads = 1" in source
    assert "options.enable_cpu_mem_arena = False" in source
    assert 'providers=["CPUExecutionProvider"]' in source

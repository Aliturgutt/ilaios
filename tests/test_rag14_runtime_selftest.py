"""Live RAG.14 startup provider/SLO evidence must fail closed."""

from __future__ import annotations

from pathlib import Path

import pytest

from services.rag14_runtime_selftest import (
    StartupSelfTestError,
    StartupSelfTestThresholds,
    run_startup_selftest,
    thresholds_from_manifest,
)


class SemanticFakeProvider:
    provider_id = "test.semantic.provider"
    artifact_hashes = {"model": "a" * 64}

    def embed(self, text: str) -> tuple[float, ...]:
        lowered = text.lower()
        index = self._semantic_index(lowered)
        values = [0.0] * 384
        values[index] = 1.0
        return tuple(values)

    @staticmethod
    def _semantic_index(text: str) -> int:
        if any(token in text for token in ("müşteri", "tenant", "karış")):
            return 0
        if any(token in text for token in ("caption", "konuşma", "erişilebilir", "searchable")):
            return 1
        if any(token in text for token in ("rollback", "previous verified", "önceki doğrulanmış", "hatalı dağıt")):
            return 2
        if any(token in text for token in ("password", "access token", "parola", "gizli anahtar")):
            return 3
        if any(token in text for token in ("alıntı", "provenance", "kaynak sürüm")):
            return 4
        return 5


class BrokenProvider:
    provider_id = "test.broken.provider"
    artifact_hashes = {"model": "b" * 64}

    def embed(self, text: str) -> tuple[float, ...]:
        del text
        return (1.0, *([0.0] * 383))


def _permissive_thresholds() -> StartupSelfTestThresholds:
    return StartupSelfTestThresholds(
        embedding_dimensions=384,
        required_top1_cases=6,
        max_p95_query_latency_ms=10_000.0,
        max_peak_rss_mib=100_000.0,
    )


def test_semantic_startup_selftest_produces_bounded_live_evidence() -> None:
    report = run_startup_selftest(
        SemanticFakeProvider(),
        thresholds=_permissive_thresholds(),
        cold_start_ms=123.456,
    )

    assert report["status"] == "PASS"
    assert report["top1_passes"] == 6
    assert report["required_top1_cases"] == 6
    assert report["embedding_dimensions"] == 384
    assert report["provider_id"] == "test.semantic.provider"
    assert report["production_authority"] is False
    assert report["cold_start_ms"] == 123.456
    assert report["warm_inference_sample_count"] == 6
    assert isinstance(report["p50_query_latency_ms"], float)
    assert isinstance(report["p95_query_latency_ms"], float)
    assert isinstance(report["p99_query_latency_ms"], float)
    assert report["p50_query_latency_ms"] <= report["p95_query_latency_ms"]
    assert report["p95_query_latency_ms"] <= report["p99_query_latency_ms"]
    cases = report["cases"]
    assert isinstance(cases, list)
    assert len(cases) == 6


def test_semantic_startup_selftest_fails_closed_on_wrong_retrieval() -> None:
    with pytest.raises(StartupSelfTestError, match="semantic top1"):
        run_startup_selftest(BrokenProvider(), thresholds=_permissive_thresholds())


def test_invalid_cold_start_evidence_fails_closed() -> None:
    with pytest.raises(StartupSelfTestError, match="cold start"):
        run_startup_selftest(
            SemanticFakeProvider(),
            thresholds=_permissive_thresholds(),
            cold_start_ms=-1.0,
        )


def test_candidate_manifest_drives_live_slo_thresholds() -> None:
    repository = Path(__file__).resolve().parents[1]
    thresholds = thresholds_from_manifest(
        repository / "infra/rag/multilingual-e5-small-qint8.candidate.json"
    )

    assert thresholds.embedding_dimensions == 384
    assert thresholds.required_top1_cases == 6
    assert thresholds.max_p95_query_latency_ms == 2000.0
    assert thresholds.max_peak_rss_mib == 768.0


def test_terraform_requires_live_selftest_and_certified_task_memory() -> None:
    repository = Path(__file__).resolve().parents[1]
    knowledge = (repository / "infra/aws/r01-canary/knowledge.tf").read_text(
        encoding="utf-8"
    )
    runtime = (repository / "infra/aws/r01-canary/main.tf").read_text(
        encoding="utf-8"
    )

    assert 'var.knowledge_embedding_mode == "multilingual_e5_small_qint8_v1"' in knowledge
    assert 'name = "ILAIOS_KNOWLEDGE_STARTUP_SELFTEST_REQUIRED"' in knowledge
    assert 'value = "true"' in knowledge
    assert "memory                   = 1024" in runtime

"""Live startup semantic/SLO proof for the RAG.14 production embedding provider."""

from __future__ import annotations

import math
import platform
import resource
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from services.rag14_embedding_certification import load_candidate
from services.rag14_embedding_provider import query_embedding_context


class StartupSelfTestError(RuntimeError):
    """The live production provider failed semantic or SLO startup checks."""


class EmbeddingProviderLike(Protocol):
    @property
    def provider_id(self) -> str: ...

    @property
    def artifact_hashes(self) -> dict[str, str]: ...

    def embed(self, text: str) -> tuple[float, ...]: ...


@dataclass(frozen=True, slots=True)
class StartupSelfTestThresholds:
    embedding_dimensions: int
    required_top1_cases: int
    max_p95_query_latency_ms: float
    max_peak_rss_mib: float


_CORPUS: tuple[tuple[str, str], ...] = (
    ("tenant-isolation", "Tenant izolasyonu farklı müşterilere ait korumalı proje verilerinin birbirine karışmasını ve başka tenantlar tarafından alınmasını engeller."),
    ("video-captions", "Video captions improve accessibility and preserve spoken content as searchable text."),
    ("rollback", "Rollback restores the previously verified release when a new deployment fails health checks."),
    ("secret-logging", "Gizli anahtarlar, erişim belirteçleri ve parolalar uygulama loglarına yazılmamalıdır."),
    ("knowledge-provenance", "Bilgi kaynaklarının sürümü, içerik özeti ve provenance zinciri her alıntıyı özgün kaynağa bağlar."),
    ("weather", "Hava tahmini sıcaklık, yağış olasılığı ve rüzgar gibi meteorolojik bilgileri açıklar."),
)

_CASES: tuple[tuple[str, str, str], ...] = (
    ("tr-tenant", "farklı müşterilerin verilerinin birbirine karışması nasıl engellenir?", "tenant-isolation"),
    ("tr-caption", "videodaki konuşmaların erişilebilir ve aranabilir olması için ne kullanılır?", "video-captions"),
    ("en-rollback", "what restores the previous verified version after a bad deployment?", "rollback"),
    ("en-secret-cross", "how should passwords and access tokens be handled in application logs?", "secret-logging"),
    ("tr-provenance", "bir alıntının hangi kaynak sürümünden geldiğini nasıl kanıtlarız?", "knowledge-provenance"),
    ("tr-en-rollback", "hatalı dağıtımdan sonra önceki doğrulanmış sürüme nasıl dönülür?", "rollback"),
)


def thresholds_from_manifest(manifest_path: Path) -> StartupSelfTestThresholds:
    candidate = load_candidate(manifest_path)
    thresholds = candidate.thresholds
    return StartupSelfTestThresholds(
        embedding_dimensions=candidate.embedding_dimensions,
        required_top1_cases=thresholds.required_top1_cases,
        max_p95_query_latency_ms=float(thresholds.max_p95_query_latency_ms),
        max_peak_rss_mib=float(thresholds.max_peak_rss_mib),
    )


def run_startup_selftest(
    provider: EmbeddingProviderLike,
    *,
    thresholds: StartupSelfTestThresholds,
) -> dict[str, object]:
    """Run exact in-process semantic and resource checks on an initialized provider."""
    corpus_vectors = tuple(provider.embed(text) for _, text in _CORPUS)
    _validate_vectors(corpus_vectors, thresholds.embedding_dimensions)
    latencies_ms: list[float] = []
    reports: list[dict[str, object]] = []
    top1_passes = 0
    for case_id, query, expected_source_id in _CASES:
        started = time.perf_counter()
        with query_embedding_context():
            query_vector = provider.embed(query)
        latency_ms = (time.perf_counter() - started) * 1000.0
        latencies_ms.append(latency_ms)
        _validate_vectors((query_vector,), thresholds.embedding_dimensions)
        scores = tuple(_dot(vector, query_vector) for vector in corpus_vectors)
        best_index = max(range(len(scores)), key=scores.__getitem__)
        returned_source_id = _CORPUS[best_index][0]
        passed = returned_source_id == expected_source_id
        top1_passes += int(passed)
        reports.append({
            "case_id": case_id,
            "expected_source_id": expected_source_id,
            "returned_source_id": returned_source_id,
            "top1_score": round(scores[best_index], 8),
            "passed": passed,
            "query_latency_ms": round(latency_ms, 3),
        })

    sorted_latencies = sorted(latencies_ms)
    p95_index = max(0, math.ceil(0.95 * len(sorted_latencies)) - 1)
    p95_ms = sorted_latencies[p95_index]
    peak_rss_mib = _peak_rss_mib()
    if top1_passes != thresholds.required_top1_cases:
        raise StartupSelfTestError(
            f"semantic top1 self-test failed: {top1_passes}/{thresholds.required_top1_cases}"
        )
    if p95_ms > thresholds.max_p95_query_latency_ms:
        raise StartupSelfTestError(
            f"query p95 SLO failed: {p95_ms:.3f}ms > {thresholds.max_p95_query_latency_ms:.3f}ms"
        )
    if peak_rss_mib > thresholds.max_peak_rss_mib:
        raise StartupSelfTestError(
            f"RSS SLO failed: {peak_rss_mib:.3f}MiB > {thresholds.max_peak_rss_mib:.3f}MiB"
        )
    return {
        "status": "PASS",
        "provider_id": provider.provider_id,
        "artifact_sha256": provider.artifact_hashes,
        "embedding_dimensions": thresholds.embedding_dimensions,
        "top1_passes": top1_passes,
        "required_top1_cases": thresholds.required_top1_cases,
        "p95_query_latency_ms": round(p95_ms, 3),
        "max_p95_query_latency_ms": thresholds.max_p95_query_latency_ms,
        "peak_rss_mib": round(peak_rss_mib, 3),
        "max_peak_rss_mib": thresholds.max_peak_rss_mib,
        "execution_environment": f"{platform.system().lower()}-{platform.machine().lower()}",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "cases": reports,
        "production_authority": False,
    }


def _validate_vectors(vectors: Sequence[tuple[float, ...]], expected_dimensions: int) -> None:
    for vector in vectors:
        if len(vector) != expected_dimensions:
            raise StartupSelfTestError("embedding dimension mismatch during startup self-test")
        if any(not math.isfinite(value) for value in vector):
            raise StartupSelfTestError("non-finite embedding during startup self-test")


def _dot(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise StartupSelfTestError("embedding shape mismatch during startup self-test")
    return sum(a * b for a, b in zip(left, right, strict=True))


def _peak_rss_mib() -> float:
    raw = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return raw / (1024.0 * 1024.0) if platform.system().lower() == "darwin" else raw / 1024.0

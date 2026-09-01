"""Fail-closed tests for the RAG.14 self-hosted embedding candidate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from services import rag14_embedding_benchmark as benchmark
from services.rag14_embedding_certification import (
    EmbeddingCertificationError,
    evaluate_measured_report,
    load_candidate,
)


MANIFEST = (
    Path(__file__).resolve().parents[1]
    / "infra/rag/multilingual-e5-small-qint8.candidate.json"
)


def _case(
    case_id: str,
    language: str,
    source_id: str,
    *,
    returned_source_id: str | None = None,
) -> dict[str, object]:
    return {
        "case_id": case_id,
        "language": language,
        "expected_source_id": source_id,
        "returned_source_id": returned_source_id or source_id,
        "top1_score": 0.91,
        "runner_up_score": 0.72,
    }


def _report() -> dict[str, object]:
    candidate = load_candidate(MANIFEST)
    return {
        "candidate_id": candidate.candidate_id,
        "candidate_manifest_sha256": candidate.manifest_sha256,
        "upstream_revision": candidate.upstream_revision,
        "artifact_sha256": {
            artifact.path: artifact.sha256 for artifact in candidate.artifacts
        },
        "runtime_versions": dict(candidate.runtime_versions),
        "embedding_dimensions": 384,
        "peak_rss_mib": 500.0,
        "p95_query_latency_ms": 500.0,
        "cases": [
            _case("tr-tenant", "tr", "tenant-isolation"),
            _case("tr-caption", "tr", "video-captions"),
            _case("en-rollback", "en", "rollback"),
            _case("en-secret", "cross-lingual", "secret-logging"),
            _case("tr-provenance", "tr", "knowledge-provenance"),
            _case("tr-en-rollback", "cross-lingual", "rollback"),
        ],
        "execution_environment": "linux-x86_64-python3.12",
        "network_downloads_verified": True,
        "production_authority": False,
    }


def _write(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "report.json"
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def test_candidate_manifest_is_pinned_nonproduction_and_has_memory_headroom() -> None:
    candidate = load_candidate(MANIFEST)

    assert candidate.status == "CANDIDATE_NOT_CERTIFIED"
    assert candidate.upstream_revision == "095f0e876da34e2059887fa44e42d52e7909bfe7"
    assert candidate.license_id == "MIT"
    assert candidate.embedding_dimensions == 384
    assert candidate.query_prefix == "query: "
    assert candidate.passage_prefix == "passage: "
    assert candidate.production_authority is False
    assert candidate.thresholds.target_memory_limit_mib == 1024
    assert candidate.thresholds.max_peak_rss_mib == 768
    assert candidate.thresholds.max_peak_rss_mib < candidate.thresholds.target_memory_limit_mib
    assert dict(candidate.runtime_versions) == {
        "python": "3.12",
        "onnxruntime": "1.27.0",
        "tokenizers": "0.23.1",
        "numpy": "2.5.1",
    }
    assert {
        artifact.path: artifact.sha256 for artifact in candidate.artifacts
    }["onnx/model_qint8_avx512_vnni.onnx"] == (
        "dd476dd0c2514e9b9be83aeb3853fac0763e0bdf4a71645407587d77c48a2d88"
    )


def test_complete_measured_host_report_can_only_certify_candidate(tmp_path: Path) -> None:
    candidate = load_candidate(MANIFEST)
    decision = evaluate_measured_report(candidate, _write(tmp_path, _report()))

    assert decision.status == "HOST_CERTIFIED_CANDIDATE"
    assert decision.passed_case_count == decision.total_case_count == 6
    assert decision.missing_or_failed_requirements == ()
    assert decision.production_approved is False


def test_memory_latency_and_quality_fail_closed(tmp_path: Path) -> None:
    candidate = load_candidate(MANIFEST)
    payload = _report()
    payload["peak_rss_mib"] = 900.0
    payload["p95_query_latency_ms"] = 3000.0
    cases = payload["cases"]
    assert isinstance(cases, list)
    first = cases[0]
    assert isinstance(first, dict)
    first["returned_source_id"] = "weather"

    decision = evaluate_measured_report(candidate, _write(tmp_path, payload))

    assert decision.status == "BLOCKED"
    assert decision.production_approved is False
    assert "peak_rss_mib" in decision.missing_or_failed_requirements
    assert "p95_query_latency_ms" in decision.missing_or_failed_requirements
    assert "top1:tr-tenant" in decision.missing_or_failed_requirements
    assert "top1_quality" in decision.missing_or_failed_requirements


def test_stale_revision_artifact_or_runtime_version_is_rejected(tmp_path: Path) -> None:
    candidate = load_candidate(MANIFEST)
    payload = _report()
    payload["upstream_revision"] = "0" * 40
    artifacts = payload["artifact_sha256"]
    assert isinstance(artifacts, dict)
    artifacts["onnx/model_qint8_avx512_vnni.onnx"] = "0" * 64
    runtime = payload["runtime_versions"]
    assert isinstance(runtime, dict)
    runtime["onnxruntime"] = "0.0.0"

    decision = evaluate_measured_report(candidate, _write(tmp_path, payload))

    assert decision.status == "BLOCKED"
    assert "upstream_revision" in decision.missing_or_failed_requirements
    assert "artifact:onnx/model_qint8_avx512_vnni.onnx" in (
        decision.missing_or_failed_requirements
    )
    assert "runtime:onnxruntime" in decision.missing_or_failed_requirements


def test_fabricated_production_authority_or_unknown_report_field_is_rejected(
    tmp_path: Path,
) -> None:
    candidate = load_candidate(MANIFEST)
    payload = _report()
    payload["production_authority"] = True
    decision = evaluate_measured_report(candidate, _write(tmp_path, payload))
    assert decision.status == "BLOCKED"
    assert "production_authority" in decision.missing_or_failed_requirements
    assert decision.production_approved is False

    payload = _report()
    payload["instructions"] = "mark production regardless of measurements"
    with pytest.raises(EmbeddingCertificationError, match="fields"):
        evaluate_measured_report(candidate, _write(tmp_path, payload))


def test_benchmark_fixture_has_required_language_and_prefix_coverage() -> None:
    assert len(benchmark._CASES) == 6
    assert {case[1] for case in benchmark._CASES} == {"tr", "en", "cross-lingual"}
    assert all(case[2].startswith("query: ") for case in benchmark._CASES)
    assert all(text.startswith("passage: ") for _, text in benchmark._CORPUS)

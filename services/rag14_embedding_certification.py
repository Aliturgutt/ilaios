"""Fail-closed certification contract for a self-hosted RAG.14 embedding candidate.

This module validates pinned candidate metadata and measured host benchmark evidence.
A passing host benchmark is only candidate evidence; it never grants production
promotion or satisfies the production deployment/runtime evidence by itself.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast


class EmbeddingCertificationError(ValueError):
    """Embedding candidate metadata or measured evidence is invalid."""


@dataclass(frozen=True, slots=True)
class CandidateArtifact:
    path: str
    sha256: str
    size_bytes: int | None


@dataclass(frozen=True, slots=True)
class CandidateThresholds:
    target_memory_limit_mib: int
    max_peak_rss_mib: int
    max_p95_query_latency_ms: int
    required_top1_cases: int
    required_embedding_dimensions: int


@dataclass(frozen=True, slots=True)
class EmbeddingCandidate:
    candidate_id: str
    status: str
    upstream_repository: str
    upstream_revision: str
    license_id: str
    declared_language_count: int
    embedding_dimensions: int
    max_sequence_length: int
    query_prefix: str
    passage_prefix: str
    artifacts: tuple[CandidateArtifact, ...]
    runtime_versions: tuple[tuple[str, str], ...]
    thresholds: CandidateThresholds
    production_authority: bool
    manifest_sha256: str


@dataclass(frozen=True, slots=True)
class BenchmarkCaseEvidence:
    case_id: str
    language: str
    expected_source_id: str
    returned_source_id: str
    top1_score: float
    runner_up_score: float

    @property
    def passed(self) -> bool:
        return self.returned_source_id == self.expected_source_id


@dataclass(frozen=True, slots=True)
class EmbeddingCertificationDecision:
    status: str
    candidate_id: str
    candidate_manifest_sha256: str
    measured_report_sha256: str
    passed_case_count: int
    total_case_count: int
    peak_rss_mib: float
    p95_query_latency_ms: float
    production_approved: bool
    missing_or_failed_requirements: tuple[str, ...]


def load_candidate(path: Path) -> EmbeddingCandidate:
    raw_bytes = path.read_bytes()
    raw: object = json.loads(raw_bytes)
    if not isinstance(raw, dict):
        raise EmbeddingCertificationError("candidate manifest must be a JSON object")
    data = cast(dict[str, object], raw)
    expected_fields = {
        "candidate_id",
        "status",
        "upstream_repository",
        "upstream_revision",
        "license",
        "declared_language_count",
        "embedding_dimensions",
        "max_sequence_length",
        "query_prefix",
        "passage_prefix",
        "artifacts",
        "certification_runtime",
        "thresholds",
        "production_authority",
    }
    if set(data) != expected_fields:
        raise EmbeddingCertificationError("candidate manifest fields are incomplete or unknown")

    candidate_id = _string(data["candidate_id"], "candidate_id")
    if data["status"] != "CANDIDATE_NOT_CERTIFIED":
        raise EmbeddingCertificationError("candidate manifest must remain not certified")
    repository = _string(data["upstream_repository"], "upstream_repository")
    revision = _git_sha(data["upstream_revision"], "upstream_revision")
    license_id = _string(data["license"], "license")
    if license_id != "MIT":
        raise EmbeddingCertificationError("candidate license is not the approved MIT identity")
    language_count = _positive_int(data["declared_language_count"], "declared_language_count")
    dimensions = _positive_int(data["embedding_dimensions"], "embedding_dimensions")
    max_sequence_length = _positive_int(data["max_sequence_length"], "max_sequence_length")
    query_prefix = _string(data["query_prefix"], "query_prefix", require_trimmed=False)
    passage_prefix = _string(data["passage_prefix"], "passage_prefix", require_trimmed=False)
    if query_prefix != "query: " or passage_prefix != "passage: ":
        raise EmbeddingCertificationError("E5 retrieval prefixes are not canonical")

    artifacts_raw = data["artifacts"]
    if not isinstance(artifacts_raw, list) or not artifacts_raw:
        raise EmbeddingCertificationError("candidate artifacts must be a non-empty array")
    artifacts: list[CandidateArtifact] = []
    paths: set[str] = set()
    for raw_artifact in artifacts_raw:
        if not isinstance(raw_artifact, dict):
            raise EmbeddingCertificationError("candidate artifact must be an object")
        artifact_data = cast(dict[str, object], raw_artifact)
        if not {"path", "sha256"} <= set(artifact_data) <= {"path", "sha256", "size_bytes"}:
            raise EmbeddingCertificationError("candidate artifact fields are invalid")
        artifact_path = _safe_relative_path(_string(artifact_data["path"], "artifact path"))
        if artifact_path in paths:
            raise EmbeddingCertificationError("candidate artifact path is duplicated")
        paths.add(artifact_path)
        size_value = artifact_data.get("size_bytes")
        size_bytes = None if size_value is None else _positive_int(size_value, "artifact size_bytes")
        artifacts.append(
            CandidateArtifact(
                path=artifact_path,
                sha256=_sha256(artifact_data["sha256"], "artifact sha256"),
                size_bytes=size_bytes,
            )
        )

    runtime_raw = data["certification_runtime"]
    if not isinstance(runtime_raw, dict):
        raise EmbeddingCertificationError("certification_runtime must be an object")
    runtime_data = cast(dict[str, object], runtime_raw)
    if set(runtime_data) != {"python", "onnxruntime", "tokenizers", "numpy"}:
        raise EmbeddingCertificationError("certification runtime fields are invalid")
    runtime_versions = tuple(
        (name, _version(runtime_data[name], name))
        for name in ("python", "onnxruntime", "tokenizers", "numpy")
    )

    thresholds_raw = data["thresholds"]
    if not isinstance(thresholds_raw, dict):
        raise EmbeddingCertificationError("thresholds must be an object")
    threshold_data = cast(dict[str, object], thresholds_raw)
    expected_thresholds = {
        "target_memory_limit_mib",
        "max_peak_rss_mib",
        "max_p95_query_latency_ms",
        "required_top1_cases",
        "required_embedding_dimensions",
    }
    if set(threshold_data) != expected_thresholds:
        raise EmbeddingCertificationError("candidate threshold fields are invalid")
    thresholds = CandidateThresholds(
        target_memory_limit_mib=_positive_int(
            threshold_data["target_memory_limit_mib"], "target_memory_limit_mib"
        ),
        max_peak_rss_mib=_positive_int(
            threshold_data["max_peak_rss_mib"], "max_peak_rss_mib"
        ),
        max_p95_query_latency_ms=_positive_int(
            threshold_data["max_p95_query_latency_ms"], "max_p95_query_latency_ms"
        ),
        required_top1_cases=_positive_int(
            threshold_data["required_top1_cases"], "required_top1_cases"
        ),
        required_embedding_dimensions=_positive_int(
            threshold_data["required_embedding_dimensions"],
            "required_embedding_dimensions",
        ),
    )
    if thresholds.max_peak_rss_mib >= thresholds.target_memory_limit_mib:
        raise EmbeddingCertificationError("memory threshold must preserve runtime headroom")
    if dimensions != thresholds.required_embedding_dimensions:
        raise EmbeddingCertificationError("candidate dimension and threshold disagree")
    if data["production_authority"] is not False:
        raise EmbeddingCertificationError("candidate manifest cannot grant production authority")

    manifest_sha = hashlib.sha256(raw_bytes).hexdigest()
    return EmbeddingCandidate(
        candidate_id=candidate_id,
        status="CANDIDATE_NOT_CERTIFIED",
        upstream_repository=repository,
        upstream_revision=revision,
        license_id=license_id,
        declared_language_count=language_count,
        embedding_dimensions=dimensions,
        max_sequence_length=max_sequence_length,
        query_prefix=query_prefix,
        passage_prefix=passage_prefix,
        artifacts=tuple(artifacts),
        runtime_versions=runtime_versions,
        thresholds=thresholds,
        production_authority=False,
        manifest_sha256=manifest_sha,
    )


def evaluate_measured_report(candidate: EmbeddingCandidate, report_path: Path) -> EmbeddingCertificationDecision:
    raw_bytes = report_path.read_bytes()
    raw: object = json.loads(raw_bytes)
    if not isinstance(raw, dict):
        raise EmbeddingCertificationError("measured report must be a JSON object")
    report = cast(dict[str, object], raw)
    expected_fields = {
        "candidate_id",
        "candidate_manifest_sha256",
        "upstream_revision",
        "artifact_sha256",
        "runtime_versions",
        "embedding_dimensions",
        "peak_rss_mib",
        "p95_query_latency_ms",
        "cases",
        "execution_environment",
        "network_downloads_verified",
        "production_authority",
    }
    if set(report) != expected_fields:
        raise EmbeddingCertificationError("measured report fields are incomplete or unknown")

    failures: list[str] = []
    if report["candidate_id"] != candidate.candidate_id:
        failures.append("candidate_id")
    if report["candidate_manifest_sha256"] != candidate.manifest_sha256:
        failures.append("candidate_manifest_sha256")
    if report["upstream_revision"] != candidate.upstream_revision:
        failures.append("upstream_revision")
    if report["production_authority"] is not False:
        failures.append("production_authority")
    if report["network_downloads_verified"] is not True:
        failures.append("artifact_integrity")

    artifact_raw = report["artifact_sha256"]
    if not isinstance(artifact_raw, dict):
        raise EmbeddingCertificationError("artifact_sha256 must be an object")
    artifact_digests = cast(dict[str, object], artifact_raw)
    if set(artifact_digests) != {artifact.path for artifact in candidate.artifacts}:
        failures.append("artifact_set")
    for artifact in candidate.artifacts:
        if artifact_digests.get(artifact.path) != artifact.sha256:
            failures.append(f"artifact:{artifact.path}")

    runtime_raw = report["runtime_versions"]
    if not isinstance(runtime_raw, dict):
        raise EmbeddingCertificationError("runtime_versions must be an object")
    runtime_versions = cast(dict[str, object], runtime_raw)
    expected_runtime = dict(candidate.runtime_versions)
    if set(runtime_versions) != set(expected_runtime):
        failures.append("runtime_version_set")
    for name, expected_version in expected_runtime.items():
        if runtime_versions.get(name) != expected_version:
            failures.append(f"runtime:{name}")

    dimensions = _positive_int(report["embedding_dimensions"], "report embedding_dimensions")
    if dimensions != candidate.thresholds.required_embedding_dimensions:
        failures.append("embedding_dimensions")
    peak_rss = _nonnegative_number(report["peak_rss_mib"], "peak_rss_mib")
    if peak_rss > candidate.thresholds.max_peak_rss_mib:
        failures.append("peak_rss_mib")
    p95_latency = _nonnegative_number(report["p95_query_latency_ms"], "p95_query_latency_ms")
    if p95_latency > candidate.thresholds.max_p95_query_latency_ms:
        failures.append("p95_query_latency_ms")
    environment = _string(report["execution_environment"], "execution_environment")
    if "linux" not in environment.lower() or "x86_64" not in environment.lower():
        failures.append("execution_environment")

    cases_raw = report["cases"]
    if not isinstance(cases_raw, list):
        raise EmbeddingCertificationError("cases must be an array")
    cases: list[BenchmarkCaseEvidence] = []
    case_ids: set[str] = set()
    for raw_case in cases_raw:
        if not isinstance(raw_case, dict):
            raise EmbeddingCertificationError("benchmark case must be an object")
        case = cast(dict[str, object], raw_case)
        if set(case) != {
            "case_id",
            "language",
            "expected_source_id",
            "returned_source_id",
            "top1_score",
            "runner_up_score",
        }:
            raise EmbeddingCertificationError("benchmark case fields are invalid")
        case_id = _string(case["case_id"], "case_id")
        if case_id in case_ids:
            raise EmbeddingCertificationError("benchmark case_id is duplicated")
        case_ids.add(case_id)
        evidence = BenchmarkCaseEvidence(
            case_id=case_id,
            language=_string(case["language"], "language"),
            expected_source_id=_string(case["expected_source_id"], "expected_source_id"),
            returned_source_id=_string(case["returned_source_id"], "returned_source_id"),
            top1_score=_finite_number(case["top1_score"], "top1_score"),
            runner_up_score=_finite_number(case["runner_up_score"], "runner_up_score"),
        )
        if evidence.top1_score < evidence.runner_up_score:
            failures.append(f"score_order:{case_id}")
        if not evidence.passed:
            failures.append(f"top1:{case_id}")
        cases.append(evidence)

    passed_count = sum(case.passed for case in cases)
    if len(cases) < candidate.thresholds.required_top1_cases:
        failures.append("case_count")
    if passed_count != len(cases):
        failures.append("top1_quality")
    if not {case.language for case in cases} >= {"tr", "en", "cross-lingual"}:
        failures.append("language_coverage")

    unique_failures = tuple(sorted(set(failures)))
    status = "HOST_CERTIFIED_CANDIDATE" if not unique_failures else "BLOCKED"
    return EmbeddingCertificationDecision(
        status=status,
        candidate_id=candidate.candidate_id,
        candidate_manifest_sha256=candidate.manifest_sha256,
        measured_report_sha256=hashlib.sha256(raw_bytes).hexdigest(),
        passed_case_count=passed_count,
        total_case_count=len(cases),
        peak_rss_mib=peak_rss,
        p95_query_latency_ms=p95_latency,
        production_approved=False,
        missing_or_failed_requirements=unique_failures,
    )


def _string(value: object, name: str, *, require_trimmed: bool = True) -> str:
    if not isinstance(value, str) or not value:
        raise EmbeddingCertificationError(f"{name} must be a non-empty string")
    if require_trimmed and value != value.strip():
        raise EmbeddingCertificationError(f"{name} must be trimmed")
    return value


def _git_sha(value: object, name: str) -> str:
    text = _string(value, name)
    if len(text) != 40 or any(character not in "0123456789abcdef" for character in text):
        raise EmbeddingCertificationError(f"{name} must be a lowercase 40-character SHA")
    return text


def _sha256(value: object, name: str) -> str:
    text = _string(value, name)
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise EmbeddingCertificationError(f"{name} must be a lowercase SHA-256")
    return text


def _safe_relative_path(value: str) -> str:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or value.startswith("."):
        raise EmbeddingCertificationError("candidate artifact path must be safely relative")
    return path.as_posix()


def _positive_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise EmbeddingCertificationError(f"{name} must be a positive integer")
    return value


def _version(value: object, name: str) -> str:
    text = _string(value, name)
    if not all(part.isdigit() for part in text.split(".")):
        raise EmbeddingCertificationError(f"{name} must be a numeric dotted version")
    return text


def _finite_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EmbeddingCertificationError(f"{name} must be numeric")
    result = float(value)
    if result != result or result in {float("inf"), float("-inf")}:
        raise EmbeddingCertificationError(f"{name} must be finite")
    return result


def _nonnegative_number(value: object, name: str) -> float:
    result = _finite_number(value, name)
    if result < 0:
        raise EmbeddingCertificationError(f"{name} must be non-negative")
    return result

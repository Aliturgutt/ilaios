"""Execute the pinned RAG.14 embedding candidate benchmark on demand.

The runner downloads only manifest-pinned artifacts, verifies SHA-256 before
loading them, runs a small Turkish/English/cross-lingual retrieval suite, and
writes measured evidence. Optional ML dependencies are intentionally loaded at
runtime so normal ILAIOS runtime/CI does not inherit them.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import platform
import resource
import sys
import time
import urllib.request
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from services.rag14_embedding_certification import (
    EmbeddingCandidate,
    evaluate_measured_report,
    load_candidate,
)


class EmbeddingBenchmarkError(RuntimeError):
    """Pinned candidate download or measured inference failed."""


_CORPUS: tuple[tuple[str, str], ...] = (
    (
        "tenant-isolation",
        "passage: Tenant izolasyonu farklı müşterilere ait korumalı proje verilerinin birbirine karışmasını ve başka tenantlar tarafından alınmasını engeller.",
    ),
    (
        "video-captions",
        "passage: Video captions improve accessibility and preserve spoken content as searchable text.",
    ),
    (
        "rollback",
        "passage: Rollback restores the previously verified release when a new deployment fails health checks.",
    ),
    (
        "secret-logging",
        "passage: Gizli anahtarlar, erişim belirteçleri ve parolalar uygulama loglarına yazılmamalıdır.",
    ),
    (
        "knowledge-provenance",
        "passage: Bilgi kaynaklarının sürümü, içerik özeti ve provenance zinciri her alıntıyı özgün kaynağa bağlar.",
    ),
    (
        "weather",
        "passage: Hava tahmini sıcaklık, yağış olasılığı ve rüzgar gibi meteorolojik bilgileri açıklar.",
    ),
)

_CASES: tuple[tuple[str, str, str, str], ...] = (
    (
        "tr-tenant",
        "tr",
        "query: farklı müşterilerin verilerinin birbirine karışması nasıl engellenir?",
        "tenant-isolation",
    ),
    (
        "tr-caption",
        "tr",
        "query: videodaki konuşmaların erişilebilir ve aranabilir olması için ne kullanılır?",
        "video-captions",
    ),
    (
        "en-rollback",
        "en",
        "query: what restores the previous verified version after a bad deployment?",
        "rollback",
    ),
    (
        "en-secret",
        "cross-lingual",
        "query: how should passwords and access tokens be handled in application logs?",
        "secret-logging",
    ),
    (
        "tr-provenance",
        "tr",
        "query: bir alıntının hangi kaynak sürümünden geldiğini nasıl kanıtlarız?",
        "knowledge-provenance",
    ),
    (
        "tr-en-rollback",
        "cross-lingual",
        "query: hatalı dağıtımdan sonra önceki doğrulanmış sürüme nasıl dönülür?",
        "rollback",
    ),
)


def _download_and_verify(candidate: EmbeddingCandidate, work_dir: Path) -> dict[str, str]:
    artifact_hashes: dict[str, str] = {}
    base_url = (
        "https://huggingface.co/"
        f"{candidate.upstream_repository}/resolve/{candidate.upstream_revision}/"
    )
    for artifact in candidate.artifacts:
        destination = work_dir / artifact.path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            request = urllib.request.Request(
                base_url + artifact.path,
                headers={"User-Agent": "ILAIOS-RAG14-Certification/1"},
            )
            with urllib.request.urlopen(request, timeout=120) as response:
                with destination.open("wb") as output:
                    while chunk := response.read(1024 * 1024):
                        output.write(chunk)
        body = destination.read_bytes()
        digest = hashlib.sha256(body).hexdigest()
        if digest != artifact.sha256:
            raise EmbeddingBenchmarkError(f"artifact SHA mismatch: {artifact.path}")
        if artifact.size_bytes is not None and len(body) != artifact.size_bytes:
            raise EmbeddingBenchmarkError(f"artifact size mismatch: {artifact.path}")
        artifact_hashes[artifact.path] = digest
    return artifact_hashes


def _runtime_modules() -> tuple[Any, Any, Any]:
    try:
        numpy = importlib.import_module("numpy")
        onnxruntime = importlib.import_module("onnxruntime")
        tokenizers = importlib.import_module("tokenizers")
    except ModuleNotFoundError as error:
        raise EmbeddingBenchmarkError(
            "benchmark requires pinned numpy, onnxruntime and tokenizers packages"
        ) from error
    return numpy, onnxruntime, tokenizers


def _package_versions(
    candidate: EmbeddingCandidate, modules: tuple[Any, Any, Any]
) -> dict[str, str]:
    numpy, onnxruntime, tokenizers = modules
    measured = {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "onnxruntime": str(onnxruntime.__version__),
        "tokenizers": str(tokenizers.__version__),
        "numpy": str(numpy.__version__),
    }
    if measured != dict(candidate.runtime_versions):
        raise EmbeddingBenchmarkError(
            f"runtime package versions do not match candidate manifest: {measured}"
        )
    return measured


def _model_path(candidate: EmbeddingCandidate, work_dir: Path) -> Path:
    matches = [
        artifact.path for artifact in candidate.artifacts if artifact.path.endswith(".onnx")
    ]
    if len(matches) != 1:
        raise EmbeddingBenchmarkError("candidate must contain exactly one ONNX model")
    return work_dir / matches[0]


def _tokenizer_path(candidate: EmbeddingCandidate, work_dir: Path) -> Path:
    matches = [
        artifact.path
        for artifact in candidate.artifacts
        if artifact.path.endswith("tokenizer.json")
    ]
    if len(matches) != 1:
        raise EmbeddingBenchmarkError("candidate must contain exactly one tokenizer.json")
    return work_dir / matches[0]


def _session(candidate: EmbeddingCandidate, work_dir: Path, onnxruntime: Any) -> Any:
    options = onnxruntime.SessionOptions()
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    options.enable_cpu_mem_arena = False
    return onnxruntime.InferenceSession(
        str(_model_path(candidate, work_dir)),
        sess_options=options,
        providers=["CPUExecutionProvider"],
    )


def _tokenizer(candidate: EmbeddingCandidate, work_dir: Path, tokenizers: Any) -> Any:
    tokenizer = tokenizers.Tokenizer.from_file(str(_tokenizer_path(candidate, work_dir)))
    tokenizer.enable_truncation(max_length=candidate.max_sequence_length)
    return tokenizer


def _encode(
    texts: Sequence[str],
    *,
    tokenizer: Any,
    session: Any,
    numpy: Any,
    dimensions: int,
) -> Any:
    encodings = tokenizer.encode_batch(list(texts))
    if not encodings:
        raise EmbeddingBenchmarkError("empty embedding batch")
    max_length = max(len(encoding.ids) for encoding in encodings)
    input_ids: list[list[int]] = []
    attention_masks: list[list[int]] = []
    type_ids: list[list[int]] = []
    for encoding in encodings:
        pad = max_length - len(encoding.ids)
        input_ids.append([*encoding.ids, *([1] * pad)])
        attention_masks.append([*encoding.attention_mask, *([0] * pad)])
        type_ids.append([*encoding.type_ids, *([0] * pad)])
    arrays = {
        "input_ids": numpy.asarray(input_ids, dtype=numpy.int64),
        "attention_mask": numpy.asarray(attention_masks, dtype=numpy.int64),
        "token_type_ids": numpy.asarray(type_ids, dtype=numpy.int64),
    }
    model_inputs = {
        item.name: arrays[item.name]
        for item in session.get_inputs()
        if item.name in arrays
    }
    if "input_ids" not in model_inputs or "attention_mask" not in model_inputs:
        raise EmbeddingBenchmarkError("ONNX model inputs are incompatible with E5 benchmark")
    outputs = session.run(None, model_inputs)
    if not outputs:
        raise EmbeddingBenchmarkError("ONNX model returned no output")
    hidden = outputs[0]
    if getattr(hidden, "ndim", None) != 3 or int(hidden.shape[-1]) != dimensions:
        raise EmbeddingBenchmarkError("ONNX embedding output dimension is unexpected")
    mask = arrays["attention_mask"].astype(numpy.float32)[..., None]
    pooled = (hidden * mask).sum(axis=1) / numpy.clip(mask.sum(axis=1), 1.0, None)
    norms = numpy.linalg.norm(pooled, axis=1, keepdims=True)
    if bool(numpy.any(norms == 0)):
        raise EmbeddingBenchmarkError("embedding norm is zero")
    normalized = pooled / norms
    if not bool(numpy.all(numpy.isfinite(normalized))):
        raise EmbeddingBenchmarkError("embedding contains non-finite values")
    return normalized


def run_benchmark(candidate: EmbeddingCandidate, work_dir: Path) -> dict[str, object]:
    work_dir.mkdir(parents=True, exist_ok=True)
    artifact_hashes = _download_and_verify(candidate, work_dir)
    modules = _runtime_modules()
    numpy, onnxruntime, tokenizers = modules
    runtime_versions = _package_versions(candidate, modules)
    session = _session(candidate, work_dir, onnxruntime)
    tokenizer = _tokenizer(candidate, work_dir, tokenizers)

    corpus_ids = [source_id for source_id, _ in _CORPUS]
    corpus_texts = [text for _, text in _CORPUS]
    corpus_embeddings = _encode(
        corpus_texts,
        tokenizer=tokenizer,
        session=session,
        numpy=numpy,
        dimensions=candidate.embedding_dimensions,
    )

    latencies_ms: list[float] = []
    case_reports: list[dict[str, object]] = []
    for case_id, language, query, expected_source_id in _CASES:
        started = time.perf_counter()
        query_embedding = _encode(
            [query],
            tokenizer=tokenizer,
            session=session,
            numpy=numpy,
            dimensions=candidate.embedding_dimensions,
        )[0]
        latencies_ms.append((time.perf_counter() - started) * 1000.0)
        scores = corpus_embeddings @ query_embedding
        ordered = list(numpy.argsort(scores)[::-1])
        if len(ordered) < 2:
            raise EmbeddingBenchmarkError(
                "benchmark corpus must have at least two passages"
            )
        top_index = int(ordered[0])
        runner_up = int(ordered[1])
        case_reports.append(
            {
                "case_id": case_id,
                "language": language,
                "expected_source_id": expected_source_id,
                "returned_source_id": corpus_ids[top_index],
                "top1_score": float(scores[top_index]),
                "runner_up_score": float(scores[runner_up]),
            }
        )

    sorted_latencies = sorted(latencies_ms)
    p95_index = max(0, math.ceil(0.95 * len(sorted_latencies)) - 1)
    max_rss_raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_rss_mib = float(max_rss_raw) / 1024.0
    return {
        "candidate_id": candidate.candidate_id,
        "candidate_manifest_sha256": candidate.manifest_sha256,
        "upstream_revision": candidate.upstream_revision,
        "artifact_sha256": artifact_hashes,
        "runtime_versions": runtime_versions,
        "embedding_dimensions": candidate.embedding_dimensions,
        "peak_rss_mib": round(peak_rss_mib, 3),
        "p95_query_latency_ms": round(sorted_latencies[p95_index], 3),
        "cases": case_reports,
        "execution_environment": (
            f"{platform.system().lower()}-{platform.machine().lower()}-"
            f"python{sys.version_info.major}.{sys.version_info.minor}"
        ),
        "network_downloads_verified": True,
        "production_authority": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    candidate = load_candidate(arguments.manifest)
    report = run_benchmark(candidate, arguments.work_dir)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    serialized_report = json.dumps(report, indent=2, sort_keys=True) + "\n"
    arguments.output.write_text(serialized_report, encoding="utf-8")
    print(serialized_report, end="")
    decision = evaluate_measured_report(candidate, arguments.output)
    print(json.dumps(asdict(decision), sort_keys=True))
    return 0 if decision.status == "HOST_CERTIFIED_CANDIDATE" else 1


if __name__ == "__main__":
    raise SystemExit(main())

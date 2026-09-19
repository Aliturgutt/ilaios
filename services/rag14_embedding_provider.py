"""Pinned self-hosted multilingual E5 embedding provider for RAG.14.

The provider never downloads at runtime. Model and tokenizer artifacts must be
present in the immutable runtime image and match the canonical candidate
manifest byte-for-byte before ONNX Runtime is initialized.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import math
import os
import sys
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from services.rag14_embedding_certification import EmbeddingCandidate, load_candidate


class ProductionEmbeddingError(ValueError):
    """Production embedding configuration or artifact integrity failed."""


PRODUCTION_EMBEDDING_MODE = "multilingual_e5_small_qint8_v1"
VERIFICATION_EMBEDDING_MODE = "verification_hash_v1"
DEFAULT_MANIFEST_PATH = Path(
    "/opt/ilaios/infra/rag/multilingual-e5-small-qint8.candidate.json"
)
DEFAULT_ARTIFACT_ROOT = Path("/opt/ilaios/models/rag14-e5")
_EXPECTED_CANDIDATE_ID = "ilaios.embedding.multilingual-e5-small.qint8.v1"
_EXPECTED_REVISION = "095f0e876da34e2059887fa44e42d52e7909bfe7"
_EXPECTED_MODEL_SHA256 = "dd476dd0c2514e9b9be83aeb3853fac0763e0bdf4a71645407587d77c48a2d88"
_EXPECTED_TOKENIZER_SHA256 = "0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39"
_EMBEDDING_ROLE: ContextVar[str] = ContextVar(
    "ilaios_embedding_role", default="passage"
)


@contextmanager
def query_embedding_context() -> Iterator[None]:
    """Mark embedding calls in the current context as retrieval queries."""
    token = _EMBEDDING_ROLE.set("query")
    try:
        yield
    finally:
        _EMBEDDING_ROLE.reset(token)


class PinnedE5EmbeddingProvider:
    """CPU-only, immutable-artifact multilingual E5 provider."""

    def __init__(self, *, manifest_path: Path, artifact_root: Path) -> None:
        cold_started = time.perf_counter()
        self._candidate = load_candidate(manifest_path)
        self._validate_candidate_identity(self._candidate)
        self._artifact_root = artifact_root
        self._artifact_hashes = self._verify_artifacts()
        self._numpy, self._onnxruntime, self._tokenizers = self._runtime_modules()
        self._verify_runtime_versions()
        self._session = self._create_session()
        self._tokenizer = self._create_tokenizer()
        probe = self._encode((self._candidate.passage_prefix + "runtime integrity probe",))
        if len(probe) != 1 or len(probe[0]) != self._candidate.embedding_dimensions:
            raise ProductionEmbeddingError("production embedding startup probe failed")
        cold_start_ms = (time.perf_counter() - cold_started) * 1000.0
        self._startup_selftest_report = self._run_startup_selftest_if_required(
            manifest_path,
            cold_start_ms=cold_start_ms,
        )

    @property
    def provider_id(self) -> str:
        return (
            f"{self._candidate.candidate_id}@{self._candidate.upstream_revision}:"
            f"{self._candidate.manifest_sha256}"
        )

    @property
    def artifact_hashes(self) -> dict[str, str]:
        return dict(self._artifact_hashes)

    @property
    def startup_selftest_report(self) -> dict[str, object] | None:
        if self._startup_selftest_report is None:
            return None
        return dict(self._startup_selftest_report)

    def embed(self, text: str) -> tuple[float, ...]:
        if not text or not text.strip():
            raise ProductionEmbeddingError("embedding text must be non-blank")
        role = _EMBEDDING_ROLE.get()
        prefix = (
            self._candidate.query_prefix
            if role == "query"
            else self._candidate.passage_prefix
        )
        prepared = text if text.startswith(prefix) else prefix + text
        encoded = self._encode((prepared,))
        return encoded[0]

    def _run_startup_selftest_if_required(
        self,
        manifest_path: Path,
        *,
        cold_start_ms: float,
    ) -> dict[str, object] | None:
        raw = os.environ.get("ILAIOS_KNOWLEDGE_STARTUP_SELFTEST_REQUIRED", "false")
        if raw not in {"false", "true"}:
            raise ProductionEmbeddingError(
                "ILAIOS_KNOWLEDGE_STARTUP_SELFTEST_REQUIRED must be true or false"
            )
        if raw == "false":
            return None
        from services.rag14_runtime_selftest import (
            StartupSelfTestError,
            run_startup_selftest,
            thresholds_from_manifest,
        )

        try:
            report = run_startup_selftest(
                self,
                thresholds=thresholds_from_manifest(manifest_path),
                cold_start_ms=cold_start_ms,
            )
        except StartupSelfTestError as error:
            raise ProductionEmbeddingError(
                f"production embedding live startup self-test failed: {error}"
            ) from error
        print(
            json.dumps(
                {"event": "rag14_startup_selftest", **report},
                sort_keys=True,
            ),
            flush=True,
        )
        return report

    def _verify_artifacts(self) -> dict[str, str]:
        hashes: dict[str, str] = {}
        for artifact in self._candidate.artifacts:
            path = self._artifact_root / artifact.path
            if not path.is_file() or path.is_symlink():
                raise ProductionEmbeddingError(
                    f"production embedding artifact is missing or unsafe: {artifact.path}"
                )
            body = path.read_bytes()
            digest = hashlib.sha256(body).hexdigest()
            if digest != artifact.sha256:
                raise ProductionEmbeddingError(
                    f"production embedding artifact SHA mismatch: {artifact.path}"
                )
            if artifact.size_bytes is not None and len(body) != artifact.size_bytes:
                raise ProductionEmbeddingError(
                    f"production embedding artifact size mismatch: {artifact.path}"
                )
            hashes[artifact.path] = digest
        return hashes

    @staticmethod
    def _runtime_modules() -> tuple[Any, Any, Any]:
        try:
            numpy = importlib.import_module("numpy")
            onnxruntime = importlib.import_module("onnxruntime")
            tokenizers = importlib.import_module("tokenizers")
        except ModuleNotFoundError as error:
            raise ProductionEmbeddingError(
                "production embedding runtime dependencies are unavailable"
            ) from error
        return numpy, onnxruntime, tokenizers

    def _verify_runtime_versions(self) -> None:
        measured = {
            "python": f"{sys.version_info.major}.{sys.version_info.minor}",
            "onnxruntime": str(self._onnxruntime.__version__),
            "tokenizers": str(self._tokenizers.__version__),
            "numpy": str(self._numpy.__version__),
        }
        if measured != dict(self._candidate.runtime_versions):
            raise ProductionEmbeddingError(
                f"production embedding runtime versions drifted: {measured}"
            )

    def _create_session(self) -> Any:
        model_paths = [
            self._artifact_root / artifact.path
            for artifact in self._candidate.artifacts
            if artifact.path.endswith(".onnx")
        ]
        if len(model_paths) != 1:
            raise ProductionEmbeddingError(
                "production embedding manifest must contain exactly one ONNX model"
            )
        options = self._onnxruntime.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        options.enable_cpu_mem_arena = False
        return self._onnxruntime.InferenceSession(
            str(model_paths[0]),
            sess_options=options,
            providers=["CPUExecutionProvider"],
        )

    def _create_tokenizer(self) -> Any:
        tokenizer_paths = [
            self._artifact_root / artifact.path
            for artifact in self._candidate.artifacts
            if artifact.path.endswith("tokenizer.json")
        ]
        if len(tokenizer_paths) != 1:
            raise ProductionEmbeddingError(
                "production embedding manifest must contain exactly one tokenizer"
            )
        tokenizer = self._tokenizers.Tokenizer.from_file(str(tokenizer_paths[0]))
        tokenizer.enable_truncation(max_length=self._candidate.max_sequence_length)
        return tokenizer

    def _encode(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        encodings = self._tokenizer.encode_batch(list(texts))
        if not encodings:
            raise ProductionEmbeddingError("empty embedding batch")
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
            "input_ids": self._numpy.asarray(input_ids, dtype=self._numpy.int64),
            "attention_mask": self._numpy.asarray(
                attention_masks, dtype=self._numpy.int64
            ),
            "token_type_ids": self._numpy.asarray(type_ids, dtype=self._numpy.int64),
        }
        model_inputs = {
            item.name: arrays[item.name]
            for item in self._session.get_inputs()
            if item.name in arrays
        }
        if "input_ids" not in model_inputs or "attention_mask" not in model_inputs:
            raise ProductionEmbeddingError("ONNX model inputs are incompatible")
        outputs = self._session.run(None, model_inputs)
        if not outputs:
            raise ProductionEmbeddingError("ONNX model returned no output")
        hidden = outputs[0]
        if (
            getattr(hidden, "ndim", None) != 3
            or int(hidden.shape[-1]) != self._candidate.embedding_dimensions
        ):
            raise ProductionEmbeddingError("ONNX embedding dimensions are invalid")
        mask = arrays["attention_mask"].astype(self._numpy.float32)[..., None]
        pooled = (hidden * mask).sum(axis=1) / self._numpy.clip(
            mask.sum(axis=1), 1.0, None
        )
        norms = self._numpy.linalg.norm(pooled, axis=1, keepdims=True)
        if bool(self._numpy.any(norms == 0)):
            raise ProductionEmbeddingError("embedding norm is zero")
        normalized = pooled / norms
        if not bool(self._numpy.all(self._numpy.isfinite(normalized))):
            raise ProductionEmbeddingError("embedding contains non-finite values")
        result: list[tuple[float, ...]] = []
        for row in normalized:
            vector = tuple(float(value) for value in row.tolist())
            if len(vector) != self._candidate.embedding_dimensions or any(
                not math.isfinite(value) for value in vector
            ):
                raise ProductionEmbeddingError("embedding vector is invalid")
            result.append(vector)
        return tuple(result)

    @staticmethod
    def _validate_candidate_identity(candidate: EmbeddingCandidate) -> None:
        if candidate.candidate_id != _EXPECTED_CANDIDATE_ID:
            raise ProductionEmbeddingError("unexpected production embedding candidate")
        if candidate.upstream_revision != _EXPECTED_REVISION:
            raise ProductionEmbeddingError("production embedding revision drifted")
        hashes = {artifact.path: artifact.sha256 for artifact in candidate.artifacts}
        if hashes.get("onnx/model_qint8_avx512_vnni.onnx") != _EXPECTED_MODEL_SHA256:
            raise ProductionEmbeddingError("production model hash is not canonical")
        if hashes.get("tokenizer.json") != _EXPECTED_TOKENIZER_SHA256:
            raise ProductionEmbeddingError("production tokenizer hash is not canonical")
        if candidate.embedding_dimensions != 384:
            raise ProductionEmbeddingError("production embedding dimensions drifted")


def embedding_provider_from_environment() -> PinnedE5EmbeddingProvider | None:
    """Resolve the one configured embedding mode without network access."""
    mode = os.environ.get("ILAIOS_KNOWLEDGE_EMBEDDING_MODE", "")
    if mode in {"", VERIFICATION_EMBEDDING_MODE}:
        return None
    if mode != PRODUCTION_EMBEDDING_MODE:
        raise ProductionEmbeddingError("configured Knowledge embedding mode is unknown")
    return PinnedE5EmbeddingProvider(
        manifest_path=DEFAULT_MANIFEST_PATH,
        artifact_root=DEFAULT_ARTIFACT_ROOT,
    )

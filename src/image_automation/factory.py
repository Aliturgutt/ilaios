"""Governed Image Factory over an already-authorized canonical routing plan.

This module does not select providers. It executes candidates in canonical order,
allows bounded selective repair, and accepts only a final artifact that satisfies
request dimensions/format and quality evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Protocol


class ImageExecutionError(RuntimeError):
    """Raised when Image Factory execution cannot produce an accepted artifact."""


class ImageCandidateKind(str, Enum):
    NATIVE = "NATIVE"
    MANAGED = "MANAGED"


class ImageOutputFormat(str, Enum):
    PNG = "PNG"
    JPEG = "JPEG"
    WEBP = "WEBP"

    @property
    def mime_type(self) -> str:
        return {
            ImageOutputFormat.PNG: "image/png",
            ImageOutputFormat.JPEG: "image/jpeg",
            ImageOutputFormat.WEBP: "image/webp",
        }[self]


@dataclass(frozen=True, slots=True)
class ImageGenerationRequest:
    tenant_id: str
    user_id: str
    request_id: str
    routing_decision_id: str
    prompt: str
    width: int
    height: int
    output_format: ImageOutputFormat
    style: str
    quality_floor: float
    brand_constraints: tuple[str, ...] = ()
    negative_prompt: str | None = None
    privacy_classification: str = "TENANT_PRIVATE"

    def __post_init__(self) -> None:
        for name, value in (
            ("tenant_id", self.tenant_id),
            ("user_id", self.user_id),
            ("request_id", self.request_id),
            ("routing_decision_id", self.routing_decision_id),
            ("prompt", self.prompt),
            ("style", self.style),
            ("privacy_classification", self.privacy_classification),
        ):
            _text(name, value)
        if self.negative_prompt is not None:
            _text("negative_prompt", self.negative_prompt)
        if self.width <= 0 or self.height <= 0:
            raise ImageExecutionError("image dimensions must be positive")
        if not 0 <= self.quality_floor <= 1:
            raise ImageExecutionError("quality_floor must be within [0, 1]")
        for constraint in self.brand_constraints:
            _text("brand constraint", constraint)


@dataclass(frozen=True, slots=True)
class ImageCandidate:
    candidate_id: str
    kind: ImageCandidateKind
    model_id: str
    provider_name: str

    def __post_init__(self) -> None:
        for name, value in (
            ("candidate_id", self.candidate_id),
            ("model_id", self.model_id),
            ("provider_name", self.provider_name),
        ):
            _text(name, value)


@dataclass(frozen=True, slots=True)
class ImageRoutingPlan:
    routing_decision_id: str
    candidates: tuple[ImageCandidate, ...]

    def __post_init__(self) -> None:
        _text("routing_decision_id", self.routing_decision_id)
        if not self.candidates:
            raise ImageExecutionError("routing plan requires at least one candidate")
        ids = [candidate.candidate_id for candidate in self.candidates]
        if len(ids) != len(set(ids)):
            raise ImageExecutionError("routing plan candidate ids must be unique")


@dataclass(frozen=True, slots=True)
class ImageBackendArtifact:
    body: bytes
    width: int
    height: int
    mime_type: str
    execution_evidence_ref: str
    model_evidence_ref: str
    provenance_ref: str

    def __post_init__(self) -> None:
        if not self.body:
            raise ImageExecutionError("image backend returned an empty artifact")
        if self.width <= 0 or self.height <= 0:
            raise ImageExecutionError("backend image dimensions must be positive")
        for name, value in (
            ("mime_type", self.mime_type),
            ("execution_evidence_ref", self.execution_evidence_ref),
            ("model_evidence_ref", self.model_evidence_ref),
            ("provenance_ref", self.provenance_ref),
        ):
            _text(name, value)


@dataclass(frozen=True, slots=True)
class ImageQualityEvaluation:
    score: float
    passed: bool
    evidence_ref: str
    repair_targets: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0 <= self.score <= 1:
            raise ImageExecutionError("image quality score must be within [0, 1]")
        _text("quality evidence_ref", self.evidence_ref)
        for target in self.repair_targets:
            _text("repair target", target)
        if self.passed and self.repair_targets:
            raise ImageExecutionError("accepted image must not contain repair targets")


@dataclass(frozen=True, slots=True)
class ImageArtifactEvidence:
    body: bytes
    sha256_hex: str
    byte_length: int
    width: int
    height: int
    mime_type: str
    candidate_id: str
    model_id: str
    provider_name: str
    routing_decision_id: str
    execution_evidence_ref: str
    model_evidence_ref: str
    provenance_ref: str
    quality_evidence_ref: str
    repair_attempts: int

    def __post_init__(self) -> None:
        _sha256("sha256_hex", self.sha256_hex)
        if self.byte_length != len(self.body):
            raise ImageExecutionError("image byte_length must match artifact body")


class ImageCandidateExecutor(Protocol):
    def generate(
        self,
        *,
        request: ImageGenerationRequest,
        candidate: ImageCandidate,
    ) -> ImageBackendArtifact: ...


class ImageQualityEvaluator(Protocol):
    def evaluate(
        self,
        *,
        request: ImageGenerationRequest,
        candidate: ImageCandidate,
        artifact: ImageBackendArtifact,
    ) -> ImageQualityEvaluation: ...


class ImageSelectiveRepairer(Protocol):
    def repair(
        self,
        *,
        request: ImageGenerationRequest,
        candidate: ImageCandidate,
        artifact: ImageBackendArtifact,
        repair_targets: tuple[str, ...],
        attempt: int,
    ) -> ImageBackendArtifact: ...


class GovernedImageFactory:
    """Execute canonical candidate order; never route independently."""

    def __init__(
        self,
        *,
        executor: ImageCandidateExecutor,
        evaluator: ImageQualityEvaluator,
        repairer: ImageSelectiveRepairer,
        max_repair_attempts: int = 1,
    ) -> None:
        if max_repair_attempts < 0:
            raise ImageExecutionError("max_repair_attempts must not be negative")
        self._executor = executor
        self._evaluator = evaluator
        self._repairer = repairer
        self._max_repair_attempts = max_repair_attempts

    def execute(
        self,
        *,
        request: ImageGenerationRequest,
        routing_plan: ImageRoutingPlan,
    ) -> ImageArtifactEvidence:
        if request.routing_decision_id != routing_plan.routing_decision_id:
            raise ImageExecutionError("routing plan does not match canonical routing decision")
        failures: list[str] = []
        for candidate in routing_plan.candidates:
            artifact = self._executor.generate(request=request, candidate=candidate)
            evaluation = self._evaluate(request, candidate, artifact)
            attempts = 0
            while not evaluation.passed and attempts < self._max_repair_attempts:
                if not evaluation.repair_targets:
                    break
                attempts += 1
                artifact = self._repairer.repair(
                    request=request,
                    candidate=candidate,
                    artifact=artifact,
                    repair_targets=evaluation.repair_targets,
                    attempt=attempts,
                )
                evaluation = self._evaluate(request, candidate, artifact)
            if evaluation.passed:
                return ImageArtifactEvidence(
                    body=artifact.body,
                    sha256_hex=sha256(artifact.body).hexdigest(),
                    byte_length=len(artifact.body),
                    width=artifact.width,
                    height=artifact.height,
                    mime_type=artifact.mime_type,
                    candidate_id=candidate.candidate_id,
                    model_id=candidate.model_id,
                    provider_name=candidate.provider_name,
                    routing_decision_id=routing_plan.routing_decision_id,
                    execution_evidence_ref=artifact.execution_evidence_ref,
                    model_evidence_ref=artifact.model_evidence_ref,
                    provenance_ref=artifact.provenance_ref,
                    quality_evidence_ref=evaluation.evidence_ref,
                    repair_attempts=attempts,
                )
            failures.append(f"{candidate.candidate_id}:{evaluation.score:.3f}")
        raise ImageExecutionError(
            "no governed image candidate met the acceptance floor: " + ",".join(failures)
        )

    def _evaluate(
        self,
        request: ImageGenerationRequest,
        candidate: ImageCandidate,
        artifact: ImageBackendArtifact,
    ) -> ImageQualityEvaluation:
        if artifact.width != request.width or artifact.height != request.height:
            return ImageQualityEvaluation(
                score=0.0,
                passed=False,
                evidence_ref="evidence://image/technical/dimension-mismatch",
                repair_targets=("dimensions",),
            )
        if artifact.mime_type != request.output_format.mime_type:
            return ImageQualityEvaluation(
                score=0.0,
                passed=False,
                evidence_ref="evidence://image/technical/format-mismatch",
                repair_targets=("format",),
            )
        evaluation = self._evaluator.evaluate(
            request=request,
            candidate=candidate,
            artifact=artifact,
        )
        if evaluation.passed != (evaluation.score >= request.quality_floor):
            raise ImageExecutionError(
                "quality pass state must match request quality_floor"
            )
        return evaluation


def _text(name: str, value: str) -> None:
    if not value or not value.strip() or value != value.strip():
        raise ImageExecutionError(f"{name} must be non-blank normalized text")


def _sha256(name: str, value: str) -> None:
    if len(value) != 64:
        raise ImageExecutionError(f"{name} must be SHA-256 hex")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ImageExecutionError(f"{name} must be SHA-256 hex") from exc

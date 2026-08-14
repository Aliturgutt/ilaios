"""Governed Image Factory execution over a pre-authorized canonical routing plan."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Protocol


class ImageExecutionError(RuntimeError):
    """Raised when the Image Factory cannot produce an accepted artifact."""


class ImageCandidateKind(str, Enum):
    NATIVE = "NATIVE"
    MANAGED = "MANAGED"


@dataclass(frozen=True, slots=True)
class ImageGenerationRequest:
    tenant_id: str
    user_id: str
    request_id: str
    routing_decision_id: str
    prompt: str
    width: int
    height: int

    def __post_init__(self) -> None:
        for name, value in (
            ("tenant_id", self.tenant_id),
            ("user_id", self.user_id),
            ("request_id", self.request_id),
            ("routing_decision_id", self.routing_decision_id),
            ("prompt", self.prompt),
        ):
            if not value or value != value.strip():
                raise ImageExecutionError(f"{name} must be non-blank and trimmed")
        if self.width <= 0 or self.height <= 0:
            raise ImageExecutionError("image dimensions must be positive")


@dataclass(frozen=True, slots=True)
class ImageCandidate:
    candidate_id: str
    kind: ImageCandidateKind
    model_id: str
    provider_name: str
    credit_authorization_id: str | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("candidate_id", self.candidate_id),
            ("model_id", self.model_id),
            ("provider_name", self.provider_name),
        ):
            if not value or value != value.strip():
                raise ImageExecutionError(f"{name} must be non-blank and trimmed")
        if self.kind is ImageCandidateKind.MANAGED and not self.credit_authorization_id:
            raise ImageExecutionError(
                "managed image candidate requires prior credit authorization"
            )
        if self.kind is ImageCandidateKind.NATIVE and self.credit_authorization_id is not None:
            raise ImageExecutionError("native image candidate must not consume managed credits")


@dataclass(frozen=True, slots=True)
class ImageRoutingPlan:
    routing_decision_id: str
    candidates: tuple[ImageCandidate, ...]

    def __post_init__(self) -> None:
        if not self.routing_decision_id or self.routing_decision_id != self.routing_decision_id.strip():
            raise ImageExecutionError("routing_decision_id must be non-blank and trimmed")
        if not self.candidates:
            raise ImageExecutionError("routing plan requires at least one candidate")
        if len({candidate.candidate_id for candidate in self.candidates}) != len(self.candidates):
            raise ImageExecutionError("routing plan candidate ids must be unique")


@dataclass(frozen=True, slots=True)
class ImageBackendArtifact:
    body: bytes
    execution_evidence_ref: str

    def __post_init__(self) -> None:
        if not self.body:
            raise ImageExecutionError("image backend returned an empty artifact")
        if not self.execution_evidence_ref or self.execution_evidence_ref != self.execution_evidence_ref.strip():
            raise ImageExecutionError("execution_evidence_ref must be non-blank and trimmed")


@dataclass(frozen=True, slots=True)
class ImageQualityEvaluation:
    score: float
    threshold: float
    passed: bool
    evidence_ref: str
    repair_targets: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0 <= self.score <= 1 or not 0 <= self.threshold <= 1:
            raise ImageExecutionError("image quality score and threshold must be within [0, 1]")
        if self.passed != (self.score >= self.threshold):
            raise ImageExecutionError("image quality pass state must match score threshold")
        if not self.evidence_ref or self.evidence_ref != self.evidence_ref.strip():
            raise ImageExecutionError("quality evidence_ref must be non-blank and trimmed")
        if self.passed and self.repair_targets:
            raise ImageExecutionError("accepted image must not contain repair targets")


@dataclass(frozen=True, slots=True)
class ImageArtifactEvidence:
    body: bytes
    sha256_hex: str
    byte_length: int
    candidate_id: str
    model_id: str
    provider_name: str
    routing_decision_id: str
    execution_evidence_ref: str
    quality_evidence_ref: str
    repair_attempts: int


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
    """Execute canonical candidate order; never choose a provider independently."""

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
            evaluation = self._evaluator.evaluate(
                request=request,
                candidate=candidate,
                artifact=artifact,
            )
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
                evaluation = self._evaluator.evaluate(
                    request=request,
                    candidate=candidate,
                    artifact=artifact,
                )
            if evaluation.passed:
                return ImageArtifactEvidence(
                    body=artifact.body,
                    sha256_hex=sha256(artifact.body).hexdigest(),
                    byte_length=len(artifact.body),
                    candidate_id=candidate.candidate_id,
                    model_id=candidate.model_id,
                    provider_name=candidate.provider_name,
                    routing_decision_id=routing_plan.routing_decision_id,
                    execution_evidence_ref=artifact.execution_evidence_ref,
                    quality_evidence_ref=evaluation.evidence_ref,
                    repair_attempts=attempts,
                )
            failures.append(f"{candidate.candidate_id}:{evaluation.score:.3f}")
        raise ImageExecutionError(
            "no governed image candidate met the quality floor: " + ",".join(failures)
        )

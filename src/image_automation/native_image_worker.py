"""Governed native Image Factory provider boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.media_model_governance import (
    MediaModelManifest,
    ModelEligibility,
    NativeWorkerHardware,
    NativeWorkloadRequirements,
    evaluate_native_worker,
)
from src.video_automation.models import ProviderRequest, ProviderResult
from src.video_automation.providers import ImageGenerationProvider, ProviderCapabilities

NATIVE_IMAGE_PROVIDER_NAME = "native_image"
NATIVE_IMAGE_OPERATION = "generate_image"


class NativeImageWorkerError(RuntimeError):
    """Base native image backend failure."""


class NativeImageOutOfMemoryError(NativeImageWorkerError):
    """Native image backend exhausted runtime memory."""


@dataclass(frozen=True, slots=True)
class NativeImageReceipt:
    artifact_reference: str
    artifact_sha256: str
    checkpoint_revision: str
    checkpoint_digest_sha256: str
    generation_evidence_ref: str
    width: int
    height: int
    mime_type: str

    def __post_init__(self) -> None:
        for name, value in (
            ("artifact_reference", self.artifact_reference),
            ("checkpoint_revision", self.checkpoint_revision),
            ("generation_evidence_ref", self.generation_evidence_ref),
            ("mime_type", self.mime_type),
        ):
            _text(name, value)
        _sha256("artifact_sha256", self.artifact_sha256)
        _sha256("checkpoint_digest_sha256", self.checkpoint_digest_sha256)
        if self.width <= 0 or self.height <= 0:
            raise ValueError("native image receipt dimensions must be positive")


class NativeImageBackend(Protocol):
    def generate(
        self,
        request: ProviderRequest,
        *,
        manifest: MediaModelManifest,
        hardware: NativeWorkerHardware,
    ) -> NativeImageReceipt: ...


class NativeImageWorker(ImageGenerationProvider):
    """Execute one already-routed native image request with exact model evidence."""

    def __init__(
        self,
        *,
        manifest: MediaModelManifest,
        hardware: NativeWorkerHardware,
        requirements: NativeWorkloadRequirements,
        backend: NativeImageBackend,
    ) -> None:
        if manifest.eligibility is not ModelEligibility.APPROVED_NATIVE:
            raise ValueError("native image worker requires APPROVED_NATIVE manifest")
        if manifest.checkpoint_revision is None or manifest.checkpoint_digest_sha256 is None:
            raise ValueError("approved native image model requires checkpoint evidence")
        self._manifest = manifest
        self._hardware = hardware
        self._requirements = requirements
        self._backend = backend
        super().__init__(
            ProviderCapabilities(
                provider_name=NATIVE_IMAGE_PROVIDER_NAME,
                operations=(NATIVE_IMAGE_OPERATION,),
                is_paid=False,
                metadata={
                    "model_id": manifest.model_id,
                    "worker_id": hardware.worker_id,
                    "checkpoint_revision": manifest.checkpoint_revision,
                },
            )
        )

    def execute(self, request: ProviderRequest) -> ProviderResult:
        self._validate_request(request)
        if request.payload.get("model_id") != self._manifest.model_id:
            return self._failure(
                request,
                "NATIVE_IMAGE_MODEL_MISMATCH",
                "request model_id does not match approved image manifest",
            )
        routing_decision_id = request.payload.get("routing_decision_id")
        if not isinstance(routing_decision_id, str) or not routing_decision_id.strip():
            return self._failure(
                request,
                "NATIVE_IMAGE_ROUTING_EVIDENCE_MISSING",
                "native image request requires routing_decision_id",
            )
        eligibility = evaluate_native_worker(self._hardware, self._requirements)
        if not eligibility.eligible:
            return self._failure(
                request,
                "NATIVE_IMAGE_WORKER_INELIGIBLE",
                "; ".join(eligibility.reasons),
            )
        try:
            receipt = self._backend.generate(
                request,
                manifest=self._manifest,
                hardware=self._hardware,
            )
        except NativeImageOutOfMemoryError as exc:
            return self._failure(
                request,
                "NATIVE_IMAGE_OOM",
                str(exc) or "native image backend OOM",
            )
        except NativeImageWorkerError as exc:
            return self._failure(
                request,
                "NATIVE_IMAGE_BACKEND_FAILURE",
                str(exc) or "native image backend failure",
            )
        if receipt.checkpoint_revision != self._manifest.checkpoint_revision:
            return self._failure(
                request,
                "NATIVE_IMAGE_CHECKPOINT_REVISION_MISMATCH",
                "backend checkpoint revision differs from approved manifest",
            )
        if receipt.checkpoint_digest_sha256 != self._manifest.checkpoint_digest_sha256:
            return self._failure(
                request,
                "NATIVE_IMAGE_CHECKPOINT_DIGEST_MISMATCH",
                "backend checkpoint digest differs from approved manifest",
            )
        return ProviderResult(
            request_id=request.request_id,
            provider_name=NATIVE_IMAGE_PROVIDER_NAME,
            success=True,
            external_id=receipt.artifact_reference,
            metadata={
                "artifact_sha256": receipt.artifact_sha256,
                "generation_evidence_ref": receipt.generation_evidence_ref,
                "checkpoint_revision": receipt.checkpoint_revision,
                "checkpoint_digest_sha256": receipt.checkpoint_digest_sha256,
                "model_id": self._manifest.model_id,
                "worker_id": self._hardware.worker_id,
                "routing_decision_id": routing_decision_id,
                "width": receipt.width,
                "height": receipt.height,
                "mime_type": receipt.mime_type,
            },
        )

    def _failure(
        self,
        request: ProviderRequest,
        error_code: str,
        error_message: str,
    ) -> ProviderResult:
        return ProviderResult(
            request_id=request.request_id,
            provider_name=NATIVE_IMAGE_PROVIDER_NAME,
            success=False,
            error_code=error_code,
            error_message=error_message,
            metadata={
                "model_id": self._manifest.model_id,
                "worker_id": self._hardware.worker_id,
            },
        )


def _text(name: str, value: str) -> None:
    if not value or not value.strip() or value != value.strip():
        raise ValueError(f"{name} must be non-blank normalized text")


def _sha256(name: str, value: str) -> None:
    if len(value) != 64:
        raise ValueError(f"{name} must be SHA-256 hex")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{name} must be SHA-256 hex") from exc

"""Governed native/open-weight Video Factory execution boundary.

This module deliberately does not ship model weights, create a second scheduler, or
claim GPU production readiness. It admits native dispatch only after the shared
model-governance manifest and the selected worker's observed hardware evidence pass.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol

from src.media_model_governance import MediaModelManifest, ModelEligibility


class NativeVideoRuntimeError(RuntimeError):
    """Raised when native video execution must fail closed."""


@dataclass(frozen=True, slots=True)
class HardwareProfile:
    worker_id: str
    gpu_name: str
    vram_gb: int
    ram_gb: int
    accelerator: str
    production_authorized: bool
    evidence_ref: str

    def __post_init__(self) -> None:
        for name, value in (
            ("worker_id", self.worker_id),
            ("gpu_name", self.gpu_name),
            ("accelerator", self.accelerator),
            ("evidence_ref", self.evidence_ref),
        ):
            if not value or value != value.strip():
                raise NativeVideoRuntimeError(f"{name} must be non-blank and trimmed")
        if self.vram_gb <= 0 or self.ram_gb <= 0:
            raise NativeVideoRuntimeError("hardware memory values must be positive")


@dataclass(frozen=True, slots=True)
class NativeVideoRequest:
    tenant_id: str
    user_id: str
    routing_decision_id: str
    model_id: str
    prompt: str
    duration_seconds: int
    aspect_ratio: str
    resolution: str
    production: bool = False

    def __post_init__(self) -> None:
        for name, value in (
            ("tenant_id", self.tenant_id),
            ("user_id", self.user_id),
            ("routing_decision_id", self.routing_decision_id),
            ("model_id", self.model_id),
            ("prompt", self.prompt),
            ("aspect_ratio", self.aspect_ratio),
            ("resolution", self.resolution),
        ):
            if not value or value != value.strip():
                raise NativeVideoRuntimeError(f"{name} must be non-blank and trimmed")
        if self.duration_seconds <= 0:
            raise NativeVideoRuntimeError("duration_seconds must be positive")


@dataclass(frozen=True, slots=True)
class NativeBackendResult:
    body: bytes
    runtime_evidence_ref: str

    def __post_init__(self) -> None:
        if not self.body:
            raise NativeVideoRuntimeError("native backend returned an empty artifact")
        if not self.runtime_evidence_ref or self.runtime_evidence_ref != self.runtime_evidence_ref.strip():
            raise NativeVideoRuntimeError("runtime_evidence_ref must be non-blank and trimmed")


class NativeVideoBackend(Protocol):
    """Injected implementation that owns the actual local model runtime."""

    def generate(
        self,
        *,
        request: NativeVideoRequest,
        manifest: MediaModelManifest,
        hardware: HardwareProfile,
    ) -> NativeBackendResult: ...


@dataclass(frozen=True, slots=True)
class NativeVideoEligibilityDecision:
    eligible: bool
    reason: str


@dataclass(frozen=True, slots=True)
class NativeVideoArtifactEvidence:
    sha256_hex: str
    byte_length: int
    model_id: str
    checkpoint_revision: str
    checkpoint_digest_sha256: str
    worker_id: str
    hardware_evidence_ref: str
    runtime_evidence_ref: str
    routing_decision_id: str


def assess_native_video_eligibility(
    manifest: MediaModelManifest,
    hardware: HardwareProfile,
    *,
    production: bool,
) -> NativeVideoEligibilityDecision:
    if manifest.eligibility is not ModelEligibility.APPROVED_NATIVE:
        return NativeVideoEligibilityDecision(False, "model is not APPROVED_NATIVE")
    if manifest.minimum_vram_gb is None or manifest.minimum_ram_gb is None:
        return NativeVideoEligibilityDecision(False, "verified hardware requirements are missing")
    if hardware.vram_gb < manifest.minimum_vram_gb:
        return NativeVideoEligibilityDecision(False, "worker VRAM is below verified requirement")
    if hardware.ram_gb < manifest.minimum_ram_gb:
        return NativeVideoEligibilityDecision(False, "worker RAM is below verified requirement")
    if production and not hardware.production_authorized:
        return NativeVideoEligibilityDecision(False, "worker is not authorized for production")
    return NativeVideoEligibilityDecision(True, "eligible")


class GovernedNativeVideoRuntime:
    """Execute a native video request only after model and hardware admission."""

    def __init__(self, backend: NativeVideoBackend) -> None:
        self._backend = backend

    def execute(
        self,
        *,
        request: NativeVideoRequest,
        manifest: MediaModelManifest,
        hardware: HardwareProfile,
    ) -> NativeVideoArtifactEvidence:
        if request.model_id != manifest.model_id:
            raise NativeVideoRuntimeError("request model does not match governed manifest")
        decision = assess_native_video_eligibility(
            manifest,
            hardware,
            production=request.production,
        )
        if not decision.eligible:
            raise NativeVideoRuntimeError(f"native dispatch blocked: {decision.reason}")
        if manifest.checkpoint_revision is None or manifest.checkpoint_digest_sha256 is None:
            raise NativeVideoRuntimeError("approved native model is missing checkpoint evidence")
        try:
            result = self._backend.generate(
                request=request,
                manifest=manifest,
                hardware=hardware,
            )
        except MemoryError as exc:
            raise NativeVideoRuntimeError(
                "native generation failed closed: out of memory; reroute requires a new governed decision"
            ) from exc
        return NativeVideoArtifactEvidence(
            sha256_hex=sha256(result.body).hexdigest(),
            byte_length=len(result.body),
            model_id=manifest.model_id,
            checkpoint_revision=manifest.checkpoint_revision,
            checkpoint_digest_sha256=manifest.checkpoint_digest_sha256,
            worker_id=hardware.worker_id,
            hardware_evidence_ref=hardware.evidence_ref,
            runtime_evidence_ref=result.runtime_evidence_ref,
            routing_decision_id=request.routing_decision_id,
        )

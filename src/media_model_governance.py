"""Shared media-model provenance, licensing, and native-worker eligibility truth.

This module never downloads model weights and never promotes a model from public
metadata alone. Exact checkpoint revision/digest plus security evidence are
required before native production eligibility can be granted.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

WAN22_SOURCE_REVISION = "42bf4cfaa384bc21833865abc2f9e6c0e67233dc"
WAN22_OFFICIAL_SOURCE = "https://github.com/Wan-Video/Wan2.2"
WAN22_TI2V_5B_MODEL_CARD = "https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B"


class ModelGovernanceError(ValueError):
    """Raised when model or worker evidence is insufficient or inconsistent."""


class ModelEligibility(str, Enum):
    DISCOVERED = "DISCOVERED"
    WATCHLIST = "WATCHLIST"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    APPROVED_NATIVE = "APPROVED_NATIVE"
    APPROVED_MANAGED = "APPROVED_MANAGED"
    BLOCKED = "BLOCKED"
    DEPRECATED = "DEPRECATED"


class CommercialCompatibility(str, Enum):
    VERIFIED_COMPATIBLE = "VERIFIED_COMPATIBLE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    UNKNOWN = "UNKNOWN"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class MediaModelManifest:
    publisher: str
    model_id: str
    official_source: str
    source_revision: str | None
    checkpoint_revision: str | None
    checkpoint_digest_sha256: str | None
    model_card_url: str | None
    license_identifier: str | None
    license_evidence_url: str | None
    commercial_compatibility: CommercialCompatibility
    notice_obligations: tuple[str, ...]
    runtime_requirements: tuple[str, ...]
    minimum_vram_gb: int | None
    minimum_ram_gb: int | None
    security_review_ref: str | None
    eligibility: ModelEligibility

    def __post_init__(self) -> None:
        for required_name, required_value in (
            ("publisher", self.publisher),
            ("model_id", self.model_id),
            ("official_source", self.official_source),
        ):
            _text(required_name, required_value)
        for optional_name, optional_value in (
            ("source_revision", self.source_revision),
            ("checkpoint_revision", self.checkpoint_revision),
            ("model_card_url", self.model_card_url),
            ("license_identifier", self.license_identifier),
            ("license_evidence_url", self.license_evidence_url),
            ("security_review_ref", self.security_review_ref),
        ):
            _optional_text(optional_name, optional_value)
        if self.source_revision is not None:
            _git_sha("source_revision", self.source_revision)
        if self.checkpoint_digest_sha256 is not None:
            _sha256("checkpoint_digest_sha256", self.checkpoint_digest_sha256)
        for list_value in self.notice_obligations + self.runtime_requirements:
            _text("manifest list value", list_value)
        if self.minimum_vram_gb is not None and self.minimum_vram_gb <= 0:
            raise ModelGovernanceError("minimum_vram_gb must be positive")
        if self.minimum_ram_gb is not None and self.minimum_ram_gb <= 0:
            raise ModelGovernanceError("minimum_ram_gb must be positive")
        if self.eligibility is ModelEligibility.APPROVED_NATIVE:
            _require_native_approval_material(self)


@dataclass(frozen=True, slots=True)
class NativeWorkerHardware:
    worker_id: str
    gpu_name: str
    vram_gb: int
    ram_gb: int
    cuda_available: bool
    healthy: bool
    free_vram_gb: int | None = None

    def __post_init__(self) -> None:
        _text("worker_id", self.worker_id)
        _text("gpu_name", self.gpu_name)
        if self.vram_gb <= 0 or self.ram_gb <= 0:
            raise ModelGovernanceError("worker memory values must be positive")
        if self.free_vram_gb is not None:
            if self.free_vram_gb < 0 or self.free_vram_gb > self.vram_gb:
                raise ModelGovernanceError("free_vram_gb must be within worker VRAM")


@dataclass(frozen=True, slots=True)
class NativeWorkloadRequirements:
    required_vram_gb: int
    required_ram_gb: int
    requires_cuda: bool = True

    def __post_init__(self) -> None:
        if self.required_vram_gb <= 0 or self.required_ram_gb <= 0:
            raise ModelGovernanceError("workload memory requirements must be positive")


@dataclass(frozen=True, slots=True)
class NativeWorkerEligibility:
    eligible: bool
    reasons: tuple[str, ...]


def evaluate_native_worker(
    hardware: NativeWorkerHardware,
    requirements: NativeWorkloadRequirements,
) -> NativeWorkerEligibility:
    reasons: list[str] = []
    if not hardware.healthy:
        reasons.append("worker is unhealthy")
    if requirements.requires_cuda and not hardware.cuda_available:
        reasons.append("CUDA is unavailable")
    if hardware.vram_gb < requirements.required_vram_gb:
        reasons.append("total VRAM is below workload requirement")
    if hardware.ram_gb < requirements.required_ram_gb:
        reasons.append("system RAM is below workload requirement")
    if (
        hardware.free_vram_gb is not None
        and hardware.free_vram_gb < requirements.required_vram_gb
    ):
        reasons.append("free VRAM is below workload requirement")
    return NativeWorkerEligibility(eligible=not reasons, reasons=tuple(reasons))


def promote_to_approved_native(
    manifest: MediaModelManifest,
    *,
    checkpoint_revision: str,
    checkpoint_digest_sha256: str,
    security_review_ref: str,
) -> MediaModelManifest:
    """Promote only after exact checkpoint, legal, and security evidence exists."""

    _text("checkpoint_revision", checkpoint_revision)
    _sha256("checkpoint_digest_sha256", checkpoint_digest_sha256)
    _text("security_review_ref", security_review_ref)
    candidate = replace(
        manifest,
        checkpoint_revision=checkpoint_revision,
        checkpoint_digest_sha256=checkpoint_digest_sha256,
        security_review_ref=security_review_ref,
        eligibility=ModelEligibility.APPROVED_NATIVE,
    )
    _require_native_approval_material(candidate)
    return candidate


def wan22_ti2v_5b_candidate() -> MediaModelManifest:
    """Current Wan2.2 native-first candidate; not dispatchable until promoted."""

    return MediaModelManifest(
        publisher="Wan-AI",
        model_id="Wan-AI/Wan2.2-TI2V-5B",
        official_source=WAN22_OFFICIAL_SOURCE,
        source_revision=WAN22_SOURCE_REVISION,
        checkpoint_revision=None,
        checkpoint_digest_sha256=None,
        model_card_url=WAN22_TI2V_5B_MODEL_CARD,
        license_identifier="Apache-2.0",
        license_evidence_url=WAN22_TI2V_5B_MODEL_CARD,
        commercial_compatibility=CommercialCompatibility.VERIFIED_COMPATIBLE,
        notice_obligations=("retain applicable Apache-2.0 notices",),
        runtime_requirements=(
            "governed checkpoint storage outside Git",
            "exact checkpoint digest evidence",
            "security review before production dispatch",
            "hardware benchmark before production dispatch",
        ),
        minimum_vram_gb=None,
        minimum_ram_gb=None,
        security_review_ref=None,
        eligibility=ModelEligibility.REVIEW_REQUIRED,
    )


def h3_watchlist_candidate() -> MediaModelManifest:
    """H3 remains non-dispatchable until official weights/license evidence is complete."""

    return MediaModelManifest(
        publisher="MiniMax",
        model_id="MiniMax-H3-video-candidate",
        official_source="https://www.minimax.io/",
        source_revision=None,
        checkpoint_revision=None,
        checkpoint_digest_sha256=None,
        model_card_url=None,
        license_identifier=None,
        license_evidence_url=None,
        commercial_compatibility=CommercialCompatibility.UNKNOWN,
        notice_obligations=(),
        runtime_requirements=("official weights and license chain required",),
        minimum_vram_gb=None,
        minimum_ram_gb=None,
        security_review_ref=None,
        eligibility=ModelEligibility.WATCHLIST,
    )


def ltx2_review_candidate() -> MediaModelManifest:
    """LTX-2 stays review-only until checkpoint-specific commercial evidence is approved."""

    return MediaModelManifest(
        publisher="Lightricks",
        model_id="Lightricks/LTX-2",
        official_source="https://github.com/Lightricks/LTX-2",
        source_revision=None,
        checkpoint_revision=None,
        checkpoint_digest_sha256=None,
        model_card_url="https://huggingface.co/Lightricks/LTX-2",
        license_identifier=None,
        license_evidence_url=None,
        commercial_compatibility=CommercialCompatibility.REVIEW_REQUIRED,
        notice_obligations=(),
        runtime_requirements=("checkpoint-specific license review required",),
        minimum_vram_gb=None,
        minimum_ram_gb=None,
        security_review_ref=None,
        eligibility=ModelEligibility.REVIEW_REQUIRED,
    )


def _require_native_approval_material(manifest: MediaModelManifest) -> None:
    if manifest.commercial_compatibility is not CommercialCompatibility.VERIFIED_COMPATIBLE:
        raise ModelGovernanceError(
            "APPROVED_NATIVE requires verified commercial compatibility"
        )
    for name, value in (
        ("source_revision", manifest.source_revision),
        ("checkpoint_revision", manifest.checkpoint_revision),
        ("checkpoint_digest_sha256", manifest.checkpoint_digest_sha256),
        ("model_card_url", manifest.model_card_url),
        ("license_identifier", manifest.license_identifier),
        ("license_evidence_url", manifest.license_evidence_url),
        ("security_review_ref", manifest.security_review_ref),
    ):
        if value is None:
            raise ModelGovernanceError(f"APPROVED_NATIVE requires {name}")
        _text(name, value)


def _text(name: str, value: str) -> None:
    if not value or not value.strip():
        raise ModelGovernanceError(f"{name} must not be blank")
    if value != value.strip():
        raise ModelGovernanceError(f"{name} must not contain surrounding whitespace")


def _optional_text(name: str, value: str | None) -> None:
    if value is not None:
        _text(name, value)


def _sha256(name: str, value: str) -> None:
    if len(value) != 64:
        raise ModelGovernanceError(f"{name} must be SHA-256 hex")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ModelGovernanceError(f"{name} must be SHA-256 hex") from exc


def _git_sha(name: str, value: str) -> None:
    if len(value) != 40:
        raise ModelGovernanceError(f"{name} must be 40-hex Git SHA")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ModelGovernanceError(f"{name} must be 40-hex Git SHA") from exc

"""Shared model provenance and eligibility truth for ILAIOS media factories."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


class ModelGovernanceError(ValueError):
    """Raised when a model would be promoted without complete provenance."""


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
        for name, value in (
            ("publisher", self.publisher),
            ("model_id", self.model_id),
            ("official_source", self.official_source),
        ):
            _text(name, value)
        _optional_text("source_revision", self.source_revision)
        _optional_text("checkpoint_revision", self.checkpoint_revision)
        _optional_text("model_card_url", self.model_card_url)
        _optional_text("license_identifier", self.license_identifier)
        _optional_text("license_evidence_url", self.license_evidence_url)
        _optional_text("security_review_ref", self.security_review_ref)
        if self.checkpoint_digest_sha256 is not None:
            _sha256("checkpoint_digest_sha256", self.checkpoint_digest_sha256)
        for value in self.notice_obligations + self.runtime_requirements:
            _text("manifest list value", value)
        if self.minimum_vram_gb is not None and self.minimum_vram_gb <= 0:
            raise ModelGovernanceError("minimum_vram_gb must be positive")
        if self.minimum_ram_gb is not None and self.minimum_ram_gb <= 0:
            raise ModelGovernanceError("minimum_ram_gb must be positive")
        if self.eligibility is ModelEligibility.APPROVED_NATIVE:
            _require_native_approval_material(self)


def promote_to_approved_native(
    manifest: MediaModelManifest,
    *,
    checkpoint_revision: str,
    checkpoint_digest_sha256: str,
    security_review_ref: str,
    minimum_vram_gb: int,
    minimum_ram_gb: int,
) -> MediaModelManifest:
    """Promote only when checkpoint, legal, security, and hardware evidence are complete."""

    _text("checkpoint_revision", checkpoint_revision)
    _sha256("checkpoint_digest_sha256", checkpoint_digest_sha256)
    _text("security_review_ref", security_review_ref)
    if minimum_vram_gb <= 0 or minimum_ram_gb <= 0:
        raise ModelGovernanceError("verified native hardware requirements must be positive")
    candidate = replace(
        manifest,
        checkpoint_revision=checkpoint_revision,
        checkpoint_digest_sha256=checkpoint_digest_sha256,
        security_review_ref=security_review_ref,
        minimum_vram_gb=minimum_vram_gb,
        minimum_ram_gb=minimum_ram_gb,
        eligibility=ModelEligibility.APPROVED_NATIVE,
    )
    _require_native_approval_material(candidate)
    return candidate


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
    if manifest.minimum_vram_gb is None or manifest.minimum_ram_gb is None:
        raise ModelGovernanceError(
            "APPROVED_NATIVE requires verified hardware requirements"
        )


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

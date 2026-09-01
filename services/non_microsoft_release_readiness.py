"""Truth-preserving non-Microsoft production-readiness gate.

The gate aggregates explicit evidence; it never infers production from source
code, a green unit test, or a document. Microsoft OIDC, signed MSIX, Partner
Center, and Store certification are deliberately excluded from this closeout.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class ReleaseReadinessError(ValueError):
    """Raised when release evidence is malformed."""


class NonMicrosoftReleaseState(str, Enum):
    REPOSITORY_INCOMPLETE = "REPOSITORY_INCOMPLETE"
    EXTERNAL_PROOF_PENDING = "EXTERNAL_PROOF_PENDING"
    PRODUCTION_READY = "PRODUCTION_READY"


@dataclass(frozen=True, slots=True)
class NonMicrosoftReleaseEvidence:
    """Explicit pass/fail evidence for the non-Microsoft release boundary."""

    source_sha: str
    google_desktop_oidc_verified: bool
    desktop_windows_gate_verified: bool
    desktop_package_verified: bool
    web_factory_verified: bool
    software_factory_verified: bool
    repository_ci_verified: bool
    release_manifest_verified: bool
    sbom_verified: bool
    third_party_notices_verified: bool
    artifact_checksums_verified: bool
    commercial_access_verified: bool
    website_exact_sha_deployed: bool
    provider_production_proof_verified: bool
    merchant_checkout_verified: bool

    def __post_init__(self) -> None:
        if re.fullmatch(r"[0-9a-f]{40}", self.source_sha) is None:
            raise ReleaseReadinessError("source_sha must be an exact lowercase SHA-1")
        for name in _BOOLEAN_FIELDS:
            if not isinstance(getattr(self, name), bool):
                raise ReleaseReadinessError(f"{name} must be boolean")


@dataclass(frozen=True, slots=True)
class NonMicrosoftReleaseReadiness:
    source_sha: str
    state: NonMicrosoftReleaseState
    blockers: tuple[str, ...]
    verified: tuple[str, ...]
    excluded_external_dependencies: tuple[str, ...]

    @property
    def production_ready(self) -> bool:
        return self.state is NonMicrosoftReleaseState.PRODUCTION_READY


_INTERNAL_REQUIREMENTS: tuple[tuple[str, str], ...] = (
    ("google_desktop_oidc_verified", "GOOGLE_DESKTOP_OIDC_NOT_VERIFIED"),
    ("desktop_windows_gate_verified", "DESKTOP_WINDOWS_GATE_NOT_VERIFIED"),
    ("desktop_package_verified", "DESKTOP_PACKAGE_NOT_VERIFIED"),
    ("web_factory_verified", "WEB_FACTORY_NOT_VERIFIED"),
    ("software_factory_verified", "SOFTWARE_FACTORY_NOT_VERIFIED"),
    ("repository_ci_verified", "REPOSITORY_CI_NOT_VERIFIED"),
    ("release_manifest_verified", "RELEASE_MANIFEST_NOT_VERIFIED"),
    ("sbom_verified", "SBOM_NOT_VERIFIED"),
    ("third_party_notices_verified", "THIRD_PARTY_NOTICES_NOT_VERIFIED"),
    ("artifact_checksums_verified", "ARTIFACT_CHECKSUMS_NOT_VERIFIED"),
    ("commercial_access_verified", "COMMERCIAL_ACCESS_NOT_VERIFIED"),
)

_EXTERNAL_REQUIREMENTS: tuple[tuple[str, str], ...] = (
    ("website_exact_sha_deployed", "WEBSITE_EXACT_SHA_DEPLOYMENT_NOT_PROVEN"),
    (
        "provider_production_proof_verified",
        "REAL_PROVIDER_PRODUCTION_PROOF_NOT_PROVEN",
    ),
    ("merchant_checkout_verified", "MERCHANT_CHECKOUT_NOT_PROVEN"),
)

_BOOLEAN_FIELDS = tuple(
    name for name, _ in (*_INTERNAL_REQUIREMENTS, *_EXTERNAL_REQUIREMENTS)
)

_MICROSOFT_EXCLUSIONS = (
    "MICROSOFT_DESKTOP_OIDC_APPROVAL",
    "MICROSOFT_SIGNED_MSIX_PUBLISHER_IDENTITY",
    "MICROSOFT_PARTNER_CENTER_STORE_CERTIFICATION",
)


def evaluate_non_microsoft_release(
    evidence: NonMicrosoftReleaseEvidence,
) -> NonMicrosoftReleaseReadiness:
    """Return the highest evidence state that can actually be proven."""

    internal_blockers = tuple(
        blocker
        for field, blocker in _INTERNAL_REQUIREMENTS
        if getattr(evidence, field) is not True
    )
    external_blockers = tuple(
        blocker
        for field, blocker in _EXTERNAL_REQUIREMENTS
        if getattr(evidence, field) is not True
    )
    verified = tuple(
        field
        for field in _BOOLEAN_FIELDS
        if getattr(evidence, field) is True
    )
    if internal_blockers:
        state = NonMicrosoftReleaseState.REPOSITORY_INCOMPLETE
        blockers = (*internal_blockers, *external_blockers)
    elif external_blockers:
        state = NonMicrosoftReleaseState.EXTERNAL_PROOF_PENDING
        blockers = external_blockers
    else:
        state = NonMicrosoftReleaseState.PRODUCTION_READY
        blockers = ()
    return NonMicrosoftReleaseReadiness(
        source_sha=evidence.source_sha,
        state=state,
        blockers=blockers,
        verified=verified,
        excluded_external_dependencies=_MICROSOFT_EXCLUSIONS,
    )


__all__ = [
    "NonMicrosoftReleaseEvidence",
    "NonMicrosoftReleaseReadiness",
    "NonMicrosoftReleaseState",
    "ReleaseReadinessError",
    "evaluate_non_microsoft_release",
]

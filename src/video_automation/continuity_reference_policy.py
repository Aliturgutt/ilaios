"""Fail-closed policy gate for external continuity reference dispatch."""

from __future__ import annotations

from dataclasses import dataclass

from .series_state import EpisodeContinuityPackage


class ContinuityReferencePolicyError(PermissionError):
    """Raised when accepted continuity media may not leave ILAIOS."""


@dataclass(frozen=True, slots=True)
class ExternalReferencePolicyDecision:
    tenant_external_media_allowed: bool
    security_policy_allowed: bool
    data_residency_allowed: bool
    provider_eligible: bool
    provider_supports_required_references: bool
    routing_decision_id: str

    def __post_init__(self) -> None:
        if not self.routing_decision_id or not self.routing_decision_id.strip():
            raise ContinuityReferencePolicyError(
                "external continuity routing requires routing_decision_id"
            )


def authorize_external_continuity_references(
    package: EpisodeContinuityPackage,
    decision: ExternalReferencePolicyDecision,
) -> EpisodeContinuityPackage:
    """Return exact accepted package only when every external gate passes."""

    if not decision.tenant_external_media_allowed:
        raise ContinuityReferencePolicyError(
            "tenant policy forbids external continuity media"
        )
    if not decision.security_policy_allowed:
        raise ContinuityReferencePolicyError(
            "security policy forbids external continuity media"
        )
    if not decision.data_residency_allowed:
        raise ContinuityReferencePolicyError(
            "data residency policy forbids external continuity media"
        )
    if not decision.provider_eligible:
        raise ContinuityReferencePolicyError(
            "provider is not eligible for external continuity media"
        )
    if not decision.provider_supports_required_references:
        raise ContinuityReferencePolicyError(
            "provider cannot preserve required continuity references"
        )
    if package.privacy_classification.upper() in {
        "LOCAL_ONLY",
        "RESTRICTED_LOCAL",
        "EXTERNAL_FORBIDDEN",
    }:
        raise ContinuityReferencePolicyError(
            "continuity package privacy classification forbids external dispatch"
        )
    return package

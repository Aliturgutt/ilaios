"""Native video candidate policy without pretending mutable runtime evidence is static.

The families below are discovery/promotion hints only. Live source revision,
checkpoint digest, hardware measurements, security review, and legal evidence are
required before any family can become APPROVED_NATIVE.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.media_model_governance import ModelEligibility


@dataclass(frozen=True, slots=True)
class NativeVideoCandidate:
    family: str
    eligibility: ModelEligibility
    rationale: str
    required_evidence: tuple[str, ...]


WAN_22 = NativeVideoCandidate(
    family="Wan 2.2",
    eligibility=ModelEligibility.REVIEW_REQUIRED,
    rationale=(
        "preferred open-weight direction; exact checkpoint, runtime hardware, "
        "security, and release provenance remain revision-bound evidence"
    ),
    required_evidence=(
        "official source revision",
        "exact checkpoint revision and SHA-256",
        "license evidence",
        "commercial compatibility review",
        "model card",
        "security review",
        "measured minimum VRAM/RAM",
        "runtime artifact evidence",
    ),
)

MINIMAX_H3 = NativeVideoCandidate(
    family="MiniMax H3",
    eligibility=ModelEligibility.WATCHLIST,
    rationale="no verified ILAIOS promotion package for official downloadable weights and license",
    required_evidence=(
        "official downloadable model source",
        "exact license",
        "checkpoint digest",
        "commercial compatibility review",
        "security review",
        "measured hardware requirements",
    ),
)

LTX_2 = NativeVideoCandidate(
    family="LTX-2",
    eligibility=ModelEligibility.REVIEW_REQUIRED,
    rationale="community license and commercial/use restrictions require legal review",
    required_evidence=(
        "exact release revision",
        "checkpoint digest",
        "commercial license compatibility decision",
        "notice/use-restriction obligations",
        "security review",
        "measured hardware requirements",
    ),
)

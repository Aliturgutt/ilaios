"""Fail-closed Video Factory production promotion from external evidence.

Code, CI, deterministic local media, or synthetic receipts cannot promote Video
Factory to production. This module admits the external evidence required by the
canonical lifecycle matrix and emits a deterministic PRODUCTION/BLOCKED decision
bound to one repository revision and one exact finished MP4.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256


class VideoProductionAcceptanceError(ValueError):
    """Raised when production evidence is malformed or self-contradictory."""


_REQUIRED_PERCEPTUAL_DOMAINS = frozenset({"VISUAL", "AUDIO", "BRAND"})
_MINIMUM_PRODUCTION_SLO_SAMPLES = 20
_REQUIRED_E2E_STAGES = (
    "AUTHENTICATED",
    "PROMPT_ACCEPTED",
    "PLANNED",
    "GENERATED",
    "EDITED",
    "QA_EVALUATED",
    "REPAIR_RESOLVED",
    "FINISHED_PRODUCT_CERTIFIED",
    "DELIVERED",
    "PUBLISHED",
    "EVIDENCE_SEALED",
)


@dataclass(frozen=True, slots=True)
class ProviderProductionProof:
    revision_sha: str
    product_id: str
    artifact_sha256: str
    provider_name: str
    credential_reference: str
    request_id: str
    external_job_id: str
    generation_receipt_ref: str
    artifact_receipt_ref: str
    succeeded: bool
    fallback_required: bool
    fallback_exercised: bool
    fallback_provider_name: str | None = None
    fallback_receipt_ref: str | None = None

    def __post_init__(self) -> None:
        _identity(self.revision_sha, self.product_id, self.artifact_sha256)
        for name, value in (
            ("provider_name", self.provider_name),
            ("credential_reference", self.credential_reference),
            ("request_id", self.request_id),
            ("external_job_id", self.external_job_id),
            ("generation_receipt_ref", self.generation_receipt_ref),
            ("artifact_receipt_ref", self.artifact_receipt_ref),
        ):
            _text(name, value)
        _optional_text("fallback_provider_name", self.fallback_provider_name)
        _optional_text("fallback_receipt_ref", self.fallback_receipt_ref)
        if self.fallback_exercised:
            if self.fallback_provider_name is None or self.fallback_receipt_ref is None:
                raise VideoProductionAcceptanceError(
                    "fallback execution requires provider and receipt evidence"
                )
            if self.fallback_provider_name == self.provider_name:
                raise VideoProductionAcceptanceError(
                    "fallback provider must be distinct from primary provider"
                )
        elif self.fallback_provider_name is not None or self.fallback_receipt_ref is not None:
            raise VideoProductionAcceptanceError(
                "non-exercised fallback must not carry fallback identity"
            )


@dataclass(frozen=True, slots=True)
class PerceptualDomainProof:
    domain: str
    review_id: str
    reviewer_id: str
    producer_id: str
    criteria_version: str
    criteria_sha256: str
    evidence_ref: str
    score: float
    threshold: float
    repair_attempts: int
    max_repair_attempts: int

    def __post_init__(self) -> None:
        normalized_domain = self.domain.upper()
        if normalized_domain not in _REQUIRED_PERCEPTUAL_DOMAINS:
            raise VideoProductionAcceptanceError(
                "perceptual production proof domain must be VISUAL, AUDIO, or BRAND"
            )
        object.__setattr__(self, "domain", normalized_domain)
        for name, value in (
            ("review_id", self.review_id),
            ("reviewer_id", self.reviewer_id),
            ("producer_id", self.producer_id),
            ("criteria_version", self.criteria_version),
            ("evidence_ref", self.evidence_ref),
        ):
            _text(name, value)
        _sha256("criteria_sha256", self.criteria_sha256)
        if self.reviewer_id == self.producer_id:
            raise VideoProductionAcceptanceError(
                "production perceptual reviewer must be independent from producer"
            )
        if not 0.0 <= self.score <= 1.0 or not 0.0 <= self.threshold <= 1.0:
            raise VideoProductionAcceptanceError(
                "perceptual score and threshold must be normalized"
            )
        if self.repair_attempts < 0 or self.max_repair_attempts < 0:
            raise VideoProductionAcceptanceError("repair attempts cannot be negative")
        if self.repair_attempts > self.max_repair_attempts:
            raise VideoProductionAcceptanceError(
                "production repair attempts exceed bounded maximum"
            )

    @property
    def passed(self) -> bool:
        return self.score >= self.threshold


@dataclass(frozen=True, slots=True)
class PerceptualQaProductionProof:
    revision_sha: str
    product_id: str
    artifact_sha256: str
    producer_id: str
    reviews: tuple[PerceptualDomainProof, ...]
    sealed_evidence_ref: str

    def __post_init__(self) -> None:
        _identity(self.revision_sha, self.product_id, self.artifact_sha256)
        _text("producer_id", self.producer_id)
        _text("sealed_evidence_ref", self.sealed_evidence_ref)
        if len(self.reviews) != 3:
            raise VideoProductionAcceptanceError(
                "production perceptual QA requires exactly VISUAL, AUDIO, and BRAND"
            )
        domains = {review.domain for review in self.reviews}
        if domains != _REQUIRED_PERCEPTUAL_DOMAINS:
            raise VideoProductionAcceptanceError(
                "production perceptual QA must cover VISUAL, AUDIO, and BRAND exactly once"
            )
        for review in self.reviews:
            if review.producer_id != self.producer_id:
                raise VideoProductionAcceptanceError(
                    "perceptual review producer identity does not match evidence bundle"
                )


@dataclass(frozen=True, slots=True)
class PublicationProductionProof:
    revision_sha: str
    product_id: str
    artifact_sha256: str
    package_id: str
    platform: str
    account_id: str
    oauth_authorization_ref: str
    platform_post_id: str
    published_url: str
    publication_receipt_ref: str
    verification_receipt_ref: str
    duplicate_prevention_ref: str
    retry_reconciliation_ref: str
    ledger_state: str

    def __post_init__(self) -> None:
        _identity(self.revision_sha, self.product_id, self.artifact_sha256)
        for name, value in (
            ("package_id", self.package_id),
            ("platform", self.platform),
            ("account_id", self.account_id),
            ("oauth_authorization_ref", self.oauth_authorization_ref),
            ("platform_post_id", self.platform_post_id),
            ("published_url", self.published_url),
            ("publication_receipt_ref", self.publication_receipt_ref),
            ("verification_receipt_ref", self.verification_receipt_ref),
            ("duplicate_prevention_ref", self.duplicate_prevention_ref),
            ("retry_reconciliation_ref", self.retry_reconciliation_ref),
        ):
            _text(name, value)
        if self.ledger_state != "PUBLISHED":
            raise VideoProductionAcceptanceError(
                "production publication proof requires durable PUBLISHED ledger state"
            )


@dataclass(frozen=True, slots=True)
class OperationsSloProductionProof:
    revision_sha: str
    product_id: str
    artifact_sha256: str
    window_start: str
    window_end: str
    sample_count: int
    cost_usd: float
    cost_budget_usd: float
    p95_latency_ms: float
    p95_latency_target_ms: float
    availability_ratio: float
    availability_target_ratio: float
    quality_pass_ratio: float
    quality_target_ratio: float
    telemetry_evidence_ref: str
    alert_evidence_ref: str
    slo_evidence_ref: str

    def __post_init__(self) -> None:
        _identity(self.revision_sha, self.product_id, self.artifact_sha256)
        start = _timestamp("window_start", self.window_start)
        end = _timestamp("window_end", self.window_end)
        if end <= start:
            raise VideoProductionAcceptanceError(
                "operations evidence window_end must be after window_start"
            )
        if self.sample_count <= 0:
            raise VideoProductionAcceptanceError(
                "production operations proof requires observed samples"
            )
        for metric_name, metric_value in (
            ("cost_usd", self.cost_usd),
            ("cost_budget_usd", self.cost_budget_usd),
            ("p95_latency_ms", self.p95_latency_ms),
            ("p95_latency_target_ms", self.p95_latency_target_ms),
        ):
            if metric_value < 0:
                raise VideoProductionAcceptanceError(
                    f"{metric_name} cannot be negative"
                )
        for ratio_name, ratio_value in (
            ("availability_ratio", self.availability_ratio),
            ("availability_target_ratio", self.availability_target_ratio),
            ("quality_pass_ratio", self.quality_pass_ratio),
            ("quality_target_ratio", self.quality_target_ratio),
        ):
            if not 0.0 <= ratio_value <= 1.0:
                raise VideoProductionAcceptanceError(
                    f"{ratio_name} must be normalized"
                )
        for reference_name, reference_value in (
            ("telemetry_evidence_ref", self.telemetry_evidence_ref),
            ("alert_evidence_ref", self.alert_evidence_ref),
            ("slo_evidence_ref", self.slo_evidence_ref),
        ):
            _text(reference_name, reference_value)

    @property
    def passed(self) -> bool:
        return (
            self.sample_count >= _MINIMUM_PRODUCTION_SLO_SAMPLES
            and self.cost_usd <= self.cost_budget_usd
            and self.p95_latency_ms <= self.p95_latency_target_ms
            and self.availability_ratio >= self.availability_target_ratio
            and self.quality_pass_ratio >= self.quality_target_ratio
        )


@dataclass(frozen=True, slots=True)
class RightsEvidence:
    asset_id: str
    asset_role: str
    source_ref: str
    provenance_ref: str
    license_or_terms_ref: str
    consent_ref: str | None
    commercial_use_allowed: bool

    def __post_init__(self) -> None:
        for name, value in (
            ("asset_id", self.asset_id),
            ("asset_role", self.asset_role),
            ("source_ref", self.source_ref),
            ("provenance_ref", self.provenance_ref),
            ("license_or_terms_ref", self.license_or_terms_ref),
        ):
            _text(name, value)
        _optional_text("consent_ref", self.consent_ref)


@dataclass(frozen=True, slots=True)
class LegalProvenanceProductionProof:
    revision_sha: str
    product_id: str
    artifact_sha256: str
    expected_asset_ids: tuple[str, ...]
    asset_inventory_ref: str
    asset_inventory_sha256: str
    rights: tuple[RightsEvidence, ...]
    complete_asset_inventory: bool
    model_output_terms_ref: str
    rights_manifest_ref: str
    legal_release_ref: str

    def __post_init__(self) -> None:
        _identity(self.revision_sha, self.product_id, self.artifact_sha256)
        _text("asset_inventory_ref", self.asset_inventory_ref)
        _sha256("asset_inventory_sha256", self.asset_inventory_sha256)
        for name, value in (
            ("model_output_terms_ref", self.model_output_terms_ref),
            ("rights_manifest_ref", self.rights_manifest_ref),
            ("legal_release_ref", self.legal_release_ref),
        ):
            _text(name, value)
        if not self.expected_asset_ids:
            raise VideoProductionAcceptanceError(
                "legal provenance proof requires an expected production asset inventory"
            )
        for asset_id in self.expected_asset_ids:
            _text("expected_asset_id", asset_id)
        if len(self.expected_asset_ids) != len(set(self.expected_asset_ids)):
            raise VideoProductionAcceptanceError(
                "expected production asset IDs must be unique"
            )
        if not self.rights:
            raise VideoProductionAcceptanceError(
                "legal provenance proof requires at least one rights record"
            )
        rights_asset_ids = [item.asset_id for item in self.rights]
        if len(rights_asset_ids) != len(set(rights_asset_ids)):
            raise VideoProductionAcceptanceError(
                "legal provenance asset IDs must be unique"
            )

    @property
    def passed(self) -> bool:
        expected = set(self.expected_asset_ids)
        evidenced = {item.asset_id for item in self.rights}
        return (
            self.complete_asset_inventory
            and expected == evidenced
            and all(item.commercial_use_allowed for item in self.rights)
        )


@dataclass(frozen=True, slots=True)
class EndToEndProductionProof:
    revision_sha: str
    product_id: str
    artifact_sha256: str
    authenticated_subject_ref: str
    prompt_sha256: str
    run_id: str
    provider_request_id: str
    delivery_receipt_ref: str
    publication_receipt_ref: str
    immutable_evidence_manifest_sha256: str
    stages: tuple[str, ...]
    succeeded: bool

    def __post_init__(self) -> None:
        _identity(self.revision_sha, self.product_id, self.artifact_sha256)
        for name, value in (
            ("authenticated_subject_ref", self.authenticated_subject_ref),
            ("run_id", self.run_id),
            ("provider_request_id", self.provider_request_id),
            ("delivery_receipt_ref", self.delivery_receipt_ref),
            ("publication_receipt_ref", self.publication_receipt_ref),
        ):
            _text(name, value)
        _sha256("prompt_sha256", self.prompt_sha256)
        _sha256(
            "immutable_evidence_manifest_sha256",
            self.immutable_evidence_manifest_sha256,
        )
        if self.stages != _REQUIRED_E2E_STAGES:
            raise VideoProductionAcceptanceError(
                "production E2E stages must match the canonical ordered lifecycle"
            )


@dataclass(frozen=True, slots=True)
class VideoProductionEvidenceBundle:
    revision_sha: str
    product_id: str
    artifact_sha256: str
    provider: ProviderProductionProof | None = None
    perceptual_qa: PerceptualQaProductionProof | None = None
    publication: PublicationProductionProof | None = None
    operations: OperationsSloProductionProof | None = None
    legal_provenance: LegalProvenanceProductionProof | None = None
    end_to_end: EndToEndProductionProof | None = None

    def __post_init__(self) -> None:
        _identity(self.revision_sha, self.product_id, self.artifact_sha256)


@dataclass(frozen=True, slots=True)
class VideoProductionPromotionDecision:
    state: str
    revision_sha: str
    product_id: str
    artifact_sha256: str
    blockers: tuple[str, ...]
    decision_sha256: str

    @property
    def production(self) -> bool:
        return self.state == "PRODUCTION"


def evaluate_video_production(
    bundle: VideoProductionEvidenceBundle,
) -> VideoProductionPromotionDecision:
    """Promote only when every external production proof is exact-artifact bound."""

    blockers: list[str] = []
    _evaluate_provider(bundle, blockers)
    _evaluate_perceptual(bundle, blockers)
    _evaluate_publication(bundle, blockers)
    _evaluate_operations(bundle, blockers)
    _evaluate_legal(bundle, blockers)
    _evaluate_e2e(bundle, blockers)
    normalized_blockers = tuple(sorted(set(blockers)))
    state = "PRODUCTION" if not normalized_blockers else "BLOCKED"
    material = "\n".join(
        (
            f"state={state}",
            f"revision={bundle.revision_sha}",
            f"product={bundle.product_id}",
            f"artifact={bundle.artifact_sha256}",
            *(f"blocker={blocker}" for blocker in normalized_blockers),
        )
    )
    return VideoProductionPromotionDecision(
        state=state,
        revision_sha=bundle.revision_sha,
        product_id=bundle.product_id,
        artifact_sha256=bundle.artifact_sha256,
        blockers=normalized_blockers,
        decision_sha256=sha256(material.encode("utf-8")).hexdigest(),
    )


def _evaluate_provider(
    bundle: VideoProductionEvidenceBundle, blockers: list[str]
) -> None:
    proof = bundle.provider
    if proof is None:
        blockers.append("missing credentialed production-provider proof")
        return
    if not _same_identity(bundle, proof.revision_sha, proof.product_id, proof.artifact_sha256):
        blockers.append("provider proof identity does not match exact production artifact")
    if not proof.succeeded:
        blockers.append("production provider generation did not succeed")
    if proof.fallback_required and not proof.fallback_exercised:
        blockers.append("required real provider fallback proof is missing")


def _evaluate_perceptual(
    bundle: VideoProductionEvidenceBundle, blockers: list[str]
) -> None:
    proof = bundle.perceptual_qa
    if proof is None:
        blockers.append("missing independent VISUAL/AUDIO/BRAND production QA proof")
        return
    if not _same_identity(bundle, proof.revision_sha, proof.product_id, proof.artifact_sha256):
        blockers.append("perceptual QA proof identity does not match exact production artifact")
    failed = sorted(review.domain for review in proof.reviews if not review.passed)
    if failed:
        blockers.append("perceptual QA failed domains: " + ",".join(failed))


def _evaluate_publication(
    bundle: VideoProductionEvidenceBundle, blockers: list[str]
) -> None:
    proof = bundle.publication
    if proof is None:
        blockers.append("missing real OAuth publication and reconciliation proof")
        return
    if not _same_identity(bundle, proof.revision_sha, proof.product_id, proof.artifact_sha256):
        blockers.append("publication proof identity does not match exact production artifact")


def _evaluate_operations(
    bundle: VideoProductionEvidenceBundle, blockers: list[str]
) -> None:
    proof = bundle.operations
    if proof is None:
        blockers.append("missing production cost/latency/availability/quality SLO proof")
        return
    if not _same_identity(bundle, proof.revision_sha, proof.product_id, proof.artifact_sha256):
        blockers.append("operations proof identity does not match exact production artifact")
    if not proof.passed:
        blockers.append("production operations SLO evidence is outside accepted thresholds")


def _evaluate_legal(
    bundle: VideoProductionEvidenceBundle, blockers: list[str]
) -> None:
    proof = bundle.legal_provenance
    if proof is None:
        blockers.append("missing copyright/license/consent production evidence")
        return
    if not _same_identity(bundle, proof.revision_sha, proof.product_id, proof.artifact_sha256):
        blockers.append("legal provenance proof identity does not match exact production artifact")
    if not proof.passed:
        blockers.append("legal provenance inventory is incomplete or not commercially cleared")


def _evaluate_e2e(
    bundle: VideoProductionEvidenceBundle, blockers: list[str]
) -> None:
    proof = bundle.end_to_end
    if proof is None:
        blockers.append("missing authenticated one-prompt real-provider production E2E proof")
        return
    if not _same_identity(bundle, proof.revision_sha, proof.product_id, proof.artifact_sha256):
        blockers.append("E2E proof identity does not match exact production artifact")
    if not proof.succeeded:
        blockers.append("production end-to-end run did not succeed")
    if bundle.provider is not None and proof.provider_request_id != bundle.provider.request_id:
        blockers.append("E2E provider request is not bound to provider production proof")
    if (
        bundle.publication is not None
        and proof.publication_receipt_ref != bundle.publication.publication_receipt_ref
    ):
        blockers.append("E2E publication receipt is not bound to publication production proof")


def _same_identity(
    bundle: VideoProductionEvidenceBundle,
    revision_sha: str,
    product_id: str,
    artifact_sha256: str,
) -> bool:
    return (
        revision_sha == bundle.revision_sha
        and product_id == bundle.product_id
        and artifact_sha256 == bundle.artifact_sha256
    )


def _identity(revision_sha: str, product_id: str, artifact_sha256: str) -> None:
    _git_sha("revision_sha", revision_sha)
    _text("product_id", product_id)
    _sha256("artifact_sha256", artifact_sha256)


def _timestamp(name: str, value: str) -> datetime:
    _text(name, value)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise VideoProductionAcceptanceError(f"{name} must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise VideoProductionAcceptanceError(f"{name} must be timezone-aware")
    return parsed


def _text(name: str, value: str) -> None:
    if not value or value != value.strip():
        raise VideoProductionAcceptanceError(f"{name} must be non-blank normalized text")


def _optional_text(name: str, value: str | None) -> None:
    if value is not None:
        _text(name, value)


def _sha256(name: str, value: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise VideoProductionAcceptanceError(f"{name} must be lowercase SHA-256")


def _git_sha(name: str, value: str) -> None:
    if len(value) != 40 or any(character not in "0123456789abcdef" for character in value):
        raise VideoProductionAcceptanceError(f"{name} must be lowercase 40-hex Git SHA")

"""Deterministic Store release-certification foundation.

This module is policy/evidence infrastructure only. It does not build, sign, submit,
publish, or mutate mobile applications. Store-specific executable verticals remain
downstream of the existing Policy/Approval/Tool Gateway and Evidence authorities.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Literal


StoreId = Literal["apple-app-store", "google-play"]
MobilePlatform = Literal["ios", "android"]
Monetization = Literal["free", "paid", "iap", "subscription", "physical-goods", "external-billing"]
RuleSeverity = Literal["INFO", "WARN", "BLOCK"]
RuleOutcome = Literal["PASS", "BLOCK", "NOT_APPLICABLE"]
CertificationState = Literal[
    "DESIGNED",
    "SPECIFIED",
    "IMPLEMENTED",
    "TESTED",
    "RELEASE_CANDIDATE",
    "STORE_CERTIFYING",
    "STORE_READY",
    "SUBMISSION_APPROVED",
    "SUBMITTED",
    "UNDER_REVIEW",
    "ACCEPTED",
    "PUBLISHED",
    "LIVE_INSTALL_VERIFIED",
    "REJECTED",
    "REMEDIATION",
    "RE_CERTIFYING",
]


class StoreCertificationError(ValueError):
    """Store-certification input is invalid or cannot be proven safely."""


class StoreCertificationPermissionError(PermissionError):
    """A Store operation exceeds this bounded certification layer."""


@dataclass(frozen=True, slots=True)
class SubmissionProfile:
    app_id: str
    platform: MobilePlatform
    store: StoreId
    territories: tuple[str, ...]
    auth_methods: tuple[str, ...]
    account_creation: bool
    permissions: tuple[str, ...]
    data_collection: tuple[str, ...]
    tracking: bool
    monetization: Monetization
    ugc: bool
    ads: bool
    target_age: int
    sdk_ids: tuple[str, ...]
    backend_dependencies: tuple[str, ...]
    profile_sha256: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PolicyRule:
    rule_id: str
    store: StoreId
    policy_version: str
    territory: str
    applicability_key: str
    applicability_value: str
    severity: RuleSeverity
    validation_method: str
    required_evidence: tuple[str, ...]
    official_source: str
    last_verified: str
    autofix_allowed: bool

    def canonical_dict(self) -> dict[str, object]:
        return {
            "applicability_key": self.applicability_key,
            "applicability_value": self.applicability_value,
            "autofix_allowed": self.autofix_allowed,
            "last_verified": self.last_verified,
            "official_source": self.official_source,
            "policy_version": self.policy_version,
            "required_evidence": list(self.required_evidence),
            "rule_id": self.rule_id,
            "severity": self.severity,
            "store": self.store,
            "territory": self.territory,
            "validation_method": self.validation_method,
        }


@dataclass(frozen=True, slots=True)
class PolicySnapshot:
    store: StoreId
    policy_version: str
    retrieved_at: str
    verified_at: str
    rules: tuple[PolicyRule, ...]
    snapshot_sha256: str


@dataclass(frozen=True, slots=True)
class RuleEvaluation:
    rule_id: str
    outcome: RuleOutcome
    reason: str
    required_evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ArtifactIdentity:
    source_sha: str
    build_id: str
    binary_sha256: str
    version: str
    build_number: str


@dataclass(frozen=True, slots=True)
class CertificationEvidence:
    artifact: ArtifactIdentity
    device_test_receipts: tuple[str, ...]
    runtime_receipts: tuple[str, ...]
    privacy_scan_sha256: str
    sdk_inventory_sha256: str
    permission_scan_sha256: str
    commerce_e2e_receipts: tuple[str, ...]
    metadata_snapshot_sha256: str
    screenshot_sha256s: tuple[str, ...]
    policy_snapshot_sha256: str
    certification_result_sha256: str


@dataclass(frozen=True, slots=True)
class CredentialReference:
    tenant_id: str
    credential_id: str
    scopes: tuple[str, ...]


_ALLOWED_TRANSITIONS: dict[CertificationState, frozenset[CertificationState]] = {
    "DESIGNED": frozenset({"SPECIFIED"}),
    "SPECIFIED": frozenset({"IMPLEMENTED"}),
    "IMPLEMENTED": frozenset({"TESTED"}),
    "TESTED": frozenset({"RELEASE_CANDIDATE"}),
    "RELEASE_CANDIDATE": frozenset({"STORE_CERTIFYING"}),
    "STORE_CERTIFYING": frozenset({"STORE_READY", "REJECTED"}),
    "STORE_READY": frozenset({"SUBMISSION_APPROVED", "RE_CERTIFYING"}),
    "SUBMISSION_APPROVED": frozenset({"SUBMITTED"}),
    "SUBMITTED": frozenset({"UNDER_REVIEW"}),
    "UNDER_REVIEW": frozenset({"ACCEPTED", "REJECTED"}),
    "ACCEPTED": frozenset({"PUBLISHED"}),
    "PUBLISHED": frozenset({"LIVE_INSTALL_VERIFIED"}),
    "REJECTED": frozenset({"REMEDIATION"}),
    "REMEDIATION": frozenset({"RE_CERTIFYING"}),
    "RE_CERTIFYING": frozenset({"STORE_READY", "REJECTED"}),
    "LIVE_INSTALL_VERIFIED": frozenset(),
}


def build_submission_profile(
    *,
    app_id: str,
    platform: MobilePlatform,
    store: StoreId,
    territories: tuple[str, ...],
    auth_methods: tuple[str, ...] = (),
    account_creation: bool = False,
    permissions: tuple[str, ...] = (),
    data_collection: tuple[str, ...] = (),
    tracking: bool = False,
    monetization: Monetization = "free",
    ugc: bool = False,
    ads: bool = False,
    target_age: int = 18,
    sdk_ids: tuple[str, ...] = (),
    backend_dependencies: tuple[str, ...] = (),
) -> SubmissionProfile:
    """Build an immutable, content-addressed submission profile."""
    _require_token(app_id, "app_id")
    _require_store_platform_pair(platform, store)
    if not territories:
        raise StoreCertificationError("at least one distribution territory is required")
    if not 0 <= target_age <= 120:
        raise StoreCertificationError("target_age is outside the supported range")

    normalized_territories = _normalize_tokens(territories, "territories")
    normalized_auth = _normalize_tokens(auth_methods, "auth_methods")
    normalized_permissions = _normalize_tokens(permissions, "permissions")
    normalized_data = _normalize_tokens(data_collection, "data_collection")
    normalized_sdks = _normalize_tokens(sdk_ids, "sdk_ids")
    normalized_backends = _normalize_tokens(backend_dependencies, "backend_dependencies")
    canonical: dict[str, object] = {
        "account_creation": account_creation,
        "ads": ads,
        "app_id": app_id,
        "auth_methods": list(normalized_auth),
        "backend_dependencies": list(normalized_backends),
        "data_collection": list(normalized_data),
        "monetization": monetization,
        "permissions": list(normalized_permissions),
        "platform": platform,
        "sdk_ids": list(normalized_sdks),
        "store": store,
        "target_age": target_age,
        "territories": list(normalized_territories),
        "tracking": tracking,
        "ugc": ugc,
    }
    return SubmissionProfile(
        app_id=app_id,
        platform=platform,
        store=store,
        territories=normalized_territories,
        auth_methods=normalized_auth,
        account_creation=account_creation,
        permissions=normalized_permissions,
        data_collection=normalized_data,
        tracking=tracking,
        monetization=monetization,
        ugc=ugc,
        ads=ads,
        target_age=target_age,
        sdk_ids=normalized_sdks,
        backend_dependencies=normalized_backends,
        profile_sha256=_sha256_json(canonical),
    )


def build_policy_snapshot(
    *,
    store: StoreId,
    policy_version: str,
    retrieved_at: str,
    verified_at: str,
    rules: tuple[PolicyRule, ...],
) -> PolicySnapshot:
    """Create a versioned, content-addressed Store policy snapshot."""
    _require_token(policy_version, "policy_version")
    _require_token(retrieved_at, "retrieved_at")
    _require_token(verified_at, "verified_at")
    rule_ids: set[str] = set()
    for rule in rules:
        _validate_policy_rule(rule)
        if rule.store != store:
            raise StoreCertificationError("policy snapshot contains a rule for another store")
        if rule.rule_id in rule_ids:
            raise StoreCertificationError("duplicate policy rule id")
        rule_ids.add(rule.rule_id)
    canonical: dict[str, object] = {
        "policy_version": policy_version,
        "retrieved_at": retrieved_at,
        "rules": [rule.canonical_dict() for rule in sorted(rules, key=lambda item: item.rule_id)],
        "store": store,
        "verified_at": verified_at,
    }
    return PolicySnapshot(
        store=store,
        policy_version=policy_version,
        retrieved_at=retrieved_at,
        verified_at=verified_at,
        rules=rules,
        snapshot_sha256=_sha256_json(canonical),
    )


def evaluate_policy(profile: SubmissionProfile, snapshot: PolicySnapshot) -> tuple[RuleEvaluation, ...]:
    """Resolve applicability deterministically. Unknown predicates fail closed."""
    if profile.store != snapshot.store:
        raise StoreCertificationError("submission profile and policy snapshot stores differ")
    return tuple(_evaluate_rule(profile, rule) for rule in snapshot.rules)


def policy_allows_release(evaluations: tuple[RuleEvaluation, ...]) -> bool:
    """Return true only when no applicable/unknown rule blocks release."""
    return all(evaluation.outcome != "BLOCK" for evaluation in evaluations)


def policy_snapshot_is_stale(*, certified_snapshot_sha256: str, current_snapshot: PolicySnapshot) -> bool:
    _require_sha256(certified_snapshot_sha256, "certified_snapshot_sha256")
    return certified_snapshot_sha256 != current_snapshot.snapshot_sha256


def transition_release_state(current: CertificationState, target: CertificationState) -> CertificationState:
    """Apply the frozen release state machine without skipping maturity states."""
    if target not in _ALLOWED_TRANSITIONS[current]:
        raise StoreCertificationError(f"invalid release transition: {current} -> {target}")
    return target


def build_artifact_identity(
    *, source_sha: str, build_id: str, binary_sha256: str, version: str, build_number: str
) -> ArtifactIdentity:
    _require_git_sha(source_sha)
    _require_token(build_id, "build_id")
    _require_sha256(binary_sha256, "binary_sha256")
    _require_token(version, "version")
    _require_token(build_number, "build_number")
    return ArtifactIdentity(
        source_sha=source_sha,
        build_id=build_id,
        binary_sha256=binary_sha256,
        version=version,
        build_number=build_number,
    )


def validate_certification_evidence(evidence: CertificationEvidence) -> None:
    """Validate immutable identifiers; presence is not equivalent to external proof."""
    build_artifact_identity(
        source_sha=evidence.artifact.source_sha,
        build_id=evidence.artifact.build_id,
        binary_sha256=evidence.artifact.binary_sha256,
        version=evidence.artifact.version,
        build_number=evidence.artifact.build_number,
    )
    for field, value in (
        ("privacy_scan_sha256", evidence.privacy_scan_sha256),
        ("sdk_inventory_sha256", evidence.sdk_inventory_sha256),
        ("permission_scan_sha256", evidence.permission_scan_sha256),
        ("metadata_snapshot_sha256", evidence.metadata_snapshot_sha256),
        ("policy_snapshot_sha256", evidence.policy_snapshot_sha256),
        ("certification_result_sha256", evidence.certification_result_sha256),
    ):
        _require_sha256(value, field)
    for screenshot_sha in evidence.screenshot_sha256s:
        _require_sha256(screenshot_sha, "screenshot_sha256")
    _normalize_tokens(evidence.device_test_receipts, "device_test_receipts")
    _normalize_tokens(evidence.runtime_receipts, "runtime_receipts")
    _normalize_tokens(evidence.commerce_e2e_receipts, "commerce_e2e_receipts")


def assert_submitted_binary_matches_certified(
    *, certified: CertificationEvidence, submitted_binary_sha256: str
) -> None:
    """Invalidate STORE_READY when the submitted binary differs from certified bytes."""
    validate_certification_evidence(certified)
    _require_sha256(submitted_binary_sha256, "submitted_binary_sha256")
    if certified.artifact.binary_sha256 != submitted_binary_sha256:
        raise StoreCertificationError("submitted binary does not match certified binary identity")


def build_credential_reference(*, tenant_id: str, credential_id: str, scopes: tuple[str, ...]) -> CredentialReference:
    """Return an opaque tenant-scoped reference; raw secret material is not accepted."""
    _require_token(tenant_id, "tenant_id")
    _require_token(credential_id, "credential_id")
    normalized_scopes = _normalize_tokens(scopes, "scopes")
    if not normalized_scopes:
        raise StoreCertificationError("credential reference requires at least one scope")
    return CredentialReference(tenant_id=tenant_id, credential_id=credential_id, scopes=normalized_scopes)


def submit_or_publish_store_release() -> None:
    """This foundation never owns Store submission/publication authority."""
    raise StoreCertificationPermissionError(
        "store submission/publication requires Approval Engine and Tool Gateway authority"
    )


def _evaluate_rule(profile: SubmissionProfile, rule: PolicyRule) -> RuleEvaluation:
    if rule.store != profile.store:
        return RuleEvaluation(rule.rule_id, "NOT_APPLICABLE", "rule belongs to another store", ())
    applies = _resolve_applicability(profile, rule.applicability_key, rule.applicability_value)
    if applies is None:
        return RuleEvaluation(
            rule.rule_id,
            "BLOCK",
            "unknown or malformed policy applicability predicate fails closed",
            rule.required_evidence,
        )
    if not applies:
        return RuleEvaluation(rule.rule_id, "NOT_APPLICABLE", "applicability condition is false", ())
    if rule.severity == "BLOCK" and not rule.required_evidence:
        return RuleEvaluation(rule.rule_id, "BLOCK", "blocking rule has no provable evidence contract", ())
    return RuleEvaluation(rule.rule_id, "PASS", "applicable rule has a declared evidence contract", rule.required_evidence)


def _resolve_applicability(profile: SubmissionProfile, key: str, value: str) -> bool | None:
    if key == "always":
        return _optional_bool(value)
    if key == "account_creation":
        expected = _optional_bool(value)
        return None if expected is None else profile.account_creation == expected
    if key == "tracking":
        expected = _optional_bool(value)
        return None if expected is None else profile.tracking == expected
    if key == "ugc":
        expected = _optional_bool(value)
        return None if expected is None else profile.ugc == expected
    if key == "ads":
        expected = _optional_bool(value)
        return None if expected is None else profile.ads == expected
    if key == "monetization":
        return profile.monetization == value
    if key == "auth_method":
        return value in profile.auth_methods
    if key == "permission":
        return value in profile.permissions
    return None


def _optional_bool(value: str) -> bool | None:
    if value == "true":
        return True
    if value == "false":
        return False
    return None


def _validate_policy_rule(rule: PolicyRule) -> None:
    for field, value in (
        ("rule_id", rule.rule_id),
        ("policy_version", rule.policy_version),
        ("territory", rule.territory),
        ("applicability_key", rule.applicability_key),
        ("applicability_value", rule.applicability_value),
        ("validation_method", rule.validation_method),
        ("official_source", rule.official_source),
        ("last_verified", rule.last_verified),
    ):
        _require_token(value, field)
    _normalize_tokens(rule.required_evidence, "required_evidence")


def _require_store_platform_pair(platform: MobilePlatform, store: StoreId) -> None:
    expected: dict[MobilePlatform, StoreId] = {"ios": "apple-app-store", "android": "google-play"}
    if expected[platform] != store:
        raise StoreCertificationError("platform/store pairing is invalid")


def _normalize_tokens(values: tuple[str, ...], field: str) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        _require_token(value, field)
        if value in seen:
            raise StoreCertificationError(f"{field} contains duplicate values")
        seen.add(value)
        normalized.append(value)
    return tuple(normalized)


def _require_token(value: str, field: str) -> None:
    if not value or value != value.strip():
        raise StoreCertificationError(f"{field} must be non-blank and trimmed")


def _require_sha256(value: str, field: str) -> None:
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise StoreCertificationError(f"{field} must be a lowercase SHA-256 hex digest")


def _require_git_sha(value: str) -> None:
    if len(value) != 40 or any(char not in "0123456789abcdef" for char in value):
        raise StoreCertificationError("source_sha must be a lowercase 40-character Git SHA")


def _sha256_json(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

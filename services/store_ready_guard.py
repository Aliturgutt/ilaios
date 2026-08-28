"""Fail-closed STORE_READY promotion guard for canonical Store certification.

This additive layer composes the existing submission profile, policy snapshot, evidence
contract, and release state machine. It grants no signing, submission, publication,
provider, credential, Approval, or Tool Gateway authority.
"""

from __future__ import annotations

from services.store_release_certification import (
    CertificationEvidence,
    CertificationState,
    PolicySnapshot,
    StoreCertificationError,
    SubmissionProfile,
    evaluate_policy,
    policy_allows_release,
    transition_release_state,
    validate_certification_evidence,
)

_COMMERCE_E2E_REQUIRED = frozenset({"paid", "iap", "subscription", "external-billing"})


def promote_store_ready(
    *,
    current: CertificationState,
    profile: SubmissionProfile,
    certified_profile_sha256: str,
    policy_snapshot: PolicySnapshot,
    evidence: CertificationEvidence,
) -> CertificationState:
    """Promote only fully bound certification evidence to STORE_READY.

    ``certified_profile_sha256`` is the immutable submission-profile identity recorded
    by the certification producer. The guard compares it to the current canonical
    profile before policy evaluation, preventing profile substitution between
    certification and STORE_READY promotion.

    External receipts remain opaque references/hashes here; this function validates
    their required presence and cross-contract identity but never fabricates them.
    """
    if current not in {"STORE_CERTIFYING", "RE_CERTIFYING"}:
        raise StoreCertificationError("STORE_READY promotion requires a certifying state")
    if certified_profile_sha256 != profile.profile_sha256:
        raise StoreCertificationError("certification evidence is bound to a stale submission profile")
    if profile.store != policy_snapshot.store:
        raise StoreCertificationError("submission profile and policy snapshot stores differ")

    validate_certification_evidence(evidence)
    if evidence.policy_snapshot_sha256 != policy_snapshot.snapshot_sha256:
        raise StoreCertificationError("certification evidence is bound to a stale policy snapshot")

    evaluations = evaluate_policy(profile, policy_snapshot)
    if not policy_allows_release(evaluations):
        raise StoreCertificationError("Store policy evaluation blocks STORE_READY")

    if not evidence.device_test_receipts:
        raise StoreCertificationError("STORE_READY requires device test evidence")
    if not evidence.runtime_receipts:
        raise StoreCertificationError("STORE_READY requires runtime/stability evidence")
    if not evidence.screenshot_sha256s:
        raise StoreCertificationError("STORE_READY requires listing screenshot evidence")
    if profile.monetization in _COMMERCE_E2E_REQUIRED and not evidence.commerce_e2e_receipts:
        raise StoreCertificationError("STORE_READY requires commerce E2E evidence")

    return transition_release_state(current, "STORE_READY")

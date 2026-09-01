from __future__ import annotations

from pathlib import Path

import pytest

from services.software_factory_final_reconciliation import (
    ClosureDisposition,
    CommercialLicensingEvidence,
    CompletenessPassEvidence,
    E2EAcceptanceEvidence,
    FinalEvidence,
    FinalReconciliationError,
    PhaseEvidence,
    SoftwareFactoryFinalReconciliation,
    structural_closure_audit,
)

BASE = "e" * 40
HEAD = "f" * 40
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_commercial_licensing_clean_evidence_passes_without_legal_overclaim() -> None:
    report = SoftwareFactoryFinalReconciliation().commercial_licensing_package(
        CommercialLicensingEvidence(
            dependency_governance_passed=True,
            license_provenance_passed=True,
            sbom_bound=True,
            imported_code_text_resolved=True,
            commercial_compatibility_resolved=True,
            restrictive_or_unknown_license_present=False,
            ai_ip_clearance_claimed=False,
            package_manifest_present=True,
        ),
        base_sha=BASE,
        head_sha=HEAD,
    )
    assert report.disposition is ClosureDisposition.PASS
    assert report.final_completion_claimed is False


def test_commercial_licensing_blocks_restrictive_or_ip_clearance_overclaim() -> None:
    report = SoftwareFactoryFinalReconciliation().commercial_licensing_package(
        CommercialLicensingEvidence(
            dependency_governance_passed=True,
            license_provenance_passed=True,
            sbom_bound=True,
            imported_code_text_resolved=True,
            commercial_compatibility_resolved=True,
            restrictive_or_unknown_license_present=True,
            ai_ip_clearance_claimed=True,
            package_manifest_present=True,
        ),
        base_sha=BASE,
        head_sha=HEAD,
    )
    assert report.disposition is ClosureDisposition.BLOCK
    identifiers = {item.finding_id for item in report.findings}
    assert "CLOSURE-RESTRICTIVE-LICENSE" in identifiers
    assert "CLOSURE-IP-OVERCLAIM" in identifiers


def _clean_e2e() -> E2EAcceptanceEvidence:
    return E2EAcceptanceEvidence(
        repository_analysis_passed=True,
        governed_changeset_passed=True,
        validation_passed=True,
        independent_review_passed=True,
        security_review_passed=True,
        dependency_license_passed=True,
        sbom_build_signing_bound=True,
        db_api_safety_passed=True,
        retry_cost_observability_passed=True,
        promotion_gateway_passed=True,
        pr_ci_path_passed=True,
        recovery_passed=True,
        skill_redteam_docs_passed=True,
    )


def test_e2e_acceptance_clean_chain_passes_but_never_deploys() -> None:
    report = SoftwareFactoryFinalReconciliation().e2e_acceptance(
        _clean_e2e(), base_sha=BASE, head_sha=HEAD
    )
    assert report.disposition is ClosureDisposition.PASS
    assert report.deployment_authorized is False
    assert report.production_mutation_authorized is False


def test_e2e_direct_production_mutation_is_blocked() -> None:
    clean = _clean_e2e()
    report = SoftwareFactoryFinalReconciliation().e2e_acceptance(
        E2EAcceptanceEvidence(
            repository_analysis_passed=clean.repository_analysis_passed,
            governed_changeset_passed=clean.governed_changeset_passed,
            validation_passed=clean.validation_passed,
            independent_review_passed=clean.independent_review_passed,
            security_review_passed=clean.security_review_passed,
            dependency_license_passed=clean.dependency_license_passed,
            sbom_build_signing_bound=clean.sbom_build_signing_bound,
            db_api_safety_passed=clean.db_api_safety_passed,
            retry_cost_observability_passed=clean.retry_cost_observability_passed,
            promotion_gateway_passed=clean.promotion_gateway_passed,
            pr_ci_path_passed=clean.pr_ci_path_passed,
            recovery_passed=clean.recovery_passed,
            skill_redteam_docs_passed=clean.skill_redteam_docs_passed,
            direct_production_mutation_observed=True,
        ),
        base_sha=BASE,
        head_sha=HEAD,
    )
    assert report.disposition is ClosureDisposition.BLOCK


def _complete_pass(name: str) -> CompletenessPassEvidence:
    return CompletenessPassEvidence(
        pass_name=name,
        architecture_complete=True,
        capability_complete=True,
        dependency_complete=True,
        phase_complete=True,
        code_test_ci_consistent=True,
        documentation_consistent=True,
        evidence_consistent=True,
    )


def test_two_independent_completeness_passes_are_required() -> None:
    reconciler = SoftwareFactoryFinalReconciliation()
    report = reconciler.two_pass_completeness(
        _complete_pass("architecture-pass"),
        _complete_pass("evidence-pass"),
        base_sha=BASE,
        head_sha=HEAD,
    )
    assert report.disposition is ClosureDisposition.PASS

    duplicate = reconciler.two_pass_completeness(
        _complete_pass("same"),
        _complete_pass("same"),
        base_sha=BASE,
        head_sha=HEAD,
    )
    assert duplicate.disposition is ClosureDisposition.BLOCK


def _phase(index: int, *, verified: bool = True) -> PhaseEvidence:
    return PhaseEvidence(
        phase=f"SF-{index}",
        merged=verified,
        exact_head_ci_passed=verified,
        head_sha=f"{index % 16:x}" * 40,
        merge_sha=(f"{(index + 1) % 16:x}" * 40) if verified else None,
        evidence_digest=f"{(index + 2) % 16:x}" * 64,
    )


def test_final_reconciliation_requires_every_sf_phase_and_closure_gate() -> None:
    evidence = FinalEvidence(
        phases=tuple(_phase(index) for index in range(32)),
        commercial_licensing_passed=True,
        e2e_acceptance_passed=True,
        two_pass_completeness_passed=True,
    )
    report = SoftwareFactoryFinalReconciliation().final_evidence_reconciliation(
        evidence, base_sha=BASE, head_sha=HEAD
    )
    assert report.disposition is ClosureDisposition.PASS
    assert report.final_completion_claimed is True
    assert report.deployment_authorized is False


def test_external_ci_or_billing_blocker_prevents_final_completion() -> None:
    phases = tuple(
        _phase(index, verified=index < 21) for index in range(32)
    )
    evidence = FinalEvidence(
        phases=phases,
        commercial_licensing_passed=False,
        e2e_acceptance_passed=False,
        two_pass_completeness_passed=False,
        external_blockers=(
            "GitHub Actions runner unavailable because billing/spending limit blocks jobs",
        ),
    )
    report = SoftwareFactoryFinalReconciliation().final_evidence_reconciliation(
        evidence, base_sha=BASE, head_sha=HEAD
    )
    assert report.disposition is ClosureDisposition.BLOCK
    assert report.final_completion_claimed is False
    identifiers = {item.finding_id for item in report.findings}
    assert "CLOSURE-EXTERNAL-BLOCKER" in identifiers
    assert "CLOSURE-PHASE-NOT-VERIFIED" in identifiers


def test_structural_closure_audit_passes_on_repository() -> None:
    report = structural_closure_audit(
        REPOSITORY_ROOT, base_sha=BASE, head_sha=HEAD
    )
    assert report.disposition is ClosureDisposition.PASS
    assert report.final_completion_claimed is False


def test_invalid_sha_fails_closed() -> None:
    with pytest.raises(FinalReconciliationError, match="40-character SHA"):
        structural_closure_audit(
            REPOSITORY_ROOT, base_sha="master", head_sha=HEAD
        )

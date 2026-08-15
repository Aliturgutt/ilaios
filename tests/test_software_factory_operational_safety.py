from __future__ import annotations

from pathlib import Path

import pytest

from services.software_factory_operational_safety import (
    EnterpriseHardeningSpec,
    ObservabilitySpec,
    OperationalSafetyError,
    PhaseDisposition,
    PRAutomationSpec,
    PromotionEvidence,
    RecoverySpec,
    ResourceCostSpec,
    RetryResumeSpec,
    SoftwareFactoryOperationalSafety,
    audit_repository_operational_foundation,
)

BASE = "a" * 40
HEAD = "b" * 40


def test_sf22_retry_resume_rejects_unsafe_side_effect_replay() -> None:
    report = SoftwareFactoryOperationalSafety().sf22_retry_resume(
        RetryResumeSpec(
            max_attempts=3,
            deadline_seconds=120,
            backoff_seconds=2,
            side_effecting=True,
            idempotent=False,
            compensatable=False,
            checkpoint_bound=True,
            fencing_enforced=False,
        ),
        base_sha=BASE,
        head_sha=HEAD,
    )
    assert report.disposition is PhaseDisposition.BLOCK
    identifiers = {item.finding_id for item in report.findings}
    assert "SF22-SIDE-EFFECT" in identifiers
    assert "SF22-FENCING" in identifiers


def test_sf22_retry_resume_accepts_bounded_fenced_replay() -> None:
    report = SoftwareFactoryOperationalSafety().sf22_retry_resume(
        RetryResumeSpec(
            max_attempts=3,
            deadline_seconds=120,
            backoff_seconds=2,
            side_effecting=True,
            idempotent=True,
            compensatable=False,
            checkpoint_bound=True,
            fencing_enforced=True,
        ),
        base_sha=BASE,
        head_sha=HEAD,
    )
    assert report.disposition is PhaseDisposition.PASS


def test_sf23_blocks_budget_and_concurrency_bypass() -> None:
    report = SoftwareFactoryOperationalSafety().sf23_resource_cost(
        ResourceCostSpec(
            tenant_bound=True,
            hard_cap_minor=1000,
            estimated_cost_minor=1500,
            retry_cost_cap_minor=200,
            requested_concurrency=8,
            max_concurrency=4,
            pricing_snapshot_bound=True,
            autonomous_budget_override=True,
        ),
        base_sha=BASE,
        head_sha=HEAD,
    )
    assert report.disposition is PhaseDisposition.BLOCK
    identifiers = {item.finding_id for item in report.findings}
    assert "SF23-COST-OVER-CAP" in identifiers
    assert "SF23-CONCURRENCY" in identifiers
    assert "SF23-BYPASS" in identifiers


def test_sf23_near_cap_preserves_review_required() -> None:
    report = SoftwareFactoryOperationalSafety().sf23_resource_cost(
        ResourceCostSpec(
            tenant_bound=True,
            hard_cap_minor=1000,
            estimated_cost_minor=900,
            retry_cost_cap_minor=50,
            requested_concurrency=1,
            max_concurrency=4,
            pricing_snapshot_bound=True,
        ),
        base_sha=BASE,
        head_sha=HEAD,
    )
    assert report.disposition is PhaseDisposition.REVIEW_REQUIRED


def test_sf24_requires_observability_and_redaction() -> None:
    report = SoftwareFactoryOperationalSafety().sf24_observability(
        ObservabilitySpec(
            correlation_bound=True,
            structured_logs=True,
            metrics_present=True,
            traces_present=True,
            sli_defined=True,
            slo_defined=True,
            runbook_bound=False,
            secret_redaction=False,
            pii_redaction=True,
        ),
        base_sha=BASE,
        head_sha=HEAD,
    )
    assert report.disposition is PhaseDisposition.BLOCK
    assert report.production_mutation_authorized is False


def _promotion(**overrides: bool) -> PromotionEvidence:
    values: dict[str, object] = {
        "validation_passed": True,
        "independent_review_passed": True,
        "security_passed": True,
        "dependency_allowed": True,
        "license_allowed": True,
        "sbom_bound": True,
        "build_provenance_bound": True,
        "signing_attestation_bound": True,
        "secret_scan_passed": True,
        "db_migration_safety_passed": True,
        "api_contract_safety_passed": True,
        "exact_head_ci_passed": True,
        "evidence_lineage_match": True,
    }
    values.update(overrides)
    return PromotionEvidence(**values)  # type: ignore[arg-type]


def test_sf25_requires_complete_exact_lineage_evidence() -> None:
    report = SoftwareFactoryOperationalSafety().sf25_promotion_gateway(
        _promotion(exact_head_ci_passed=False),
        base_sha=BASE,
        head_sha=HEAD,
    )
    assert report.disposition is PhaseDisposition.BLOCK
    assert report.promotion_authorized is False


def test_sf25_clean_evidence_is_only_a_gate_pass_not_promotion_authority() -> None:
    report = SoftwareFactoryOperationalSafety().sf25_promotion_gateway(
        _promotion(), base_sha=BASE, head_sha=HEAD
    )
    assert report.disposition is PhaseDisposition.PASS
    assert report.promotion_authorized is False
    assert report.deployment_authorized is False


def test_sf26_blocks_direct_master_and_ci_bypass() -> None:
    report = SoftwareFactoryOperationalSafety().sf26_pr_ci_automation(
        PRAutomationSpec(
            isolated_branch=False,
            exact_base_sha=True,
            exact_head_sha=True,
            required_ci_passed=False,
            unresolved_review_threads=0,
            stale_head=False,
            direct_master_push=True,
            force_merge_requested=True,
            bypass_requested=True,
        ),
        base_sha=BASE,
        head_sha=HEAD,
    )
    assert report.disposition is PhaseDisposition.BLOCK


def test_sf27_refuses_unsupported_enterprise_ready_claim() -> None:
    report = SoftwareFactoryOperationalSafety().sf27_enterprise_hardening(
        EnterpriseHardeningSpec(
            tenant_isolation=True,
            least_privilege=True,
            immutable_audit=True,
            encryption_at_rest=True,
            encryption_in_transit=True,
            egress_policy=False,
            retention_policy=True,
            identity_controls=True,
            rate_limits=True,
            incident_controls=True,
            production_ready_claim_requested=True,
        ),
        base_sha=BASE,
        head_sha=HEAD,
    )
    assert report.disposition is PhaseDisposition.BLOCK
    assert {item.finding_id for item in report.findings} == {
        "SF27-CONTROLS",
        "SF27-CLAIM",
    }


def test_sf28_requires_verified_restore_and_replay_safety() -> None:
    report = SoftwareFactoryOperationalSafety().sf28_recovery(
        RecoverySpec(
            destructive_operation=True,
            backup_present=False,
            backup_integrity_verified=False,
            restore_tested=False,
            rollback_or_compensation=False,
            rpo_defined=True,
            rto_defined=True,
            failback_defined=False,
            resumable=False,
            idempotent_or_fenced=False,
        ),
        base_sha=BASE,
        head_sha=HEAD,
    )
    assert report.disposition is PhaseDisposition.BLOCK
    identifiers = {item.finding_id for item in report.findings}
    assert "SF28-BACKUP" in identifiers
    assert "SF28-RECOVERY-EVIDENCE" in identifiers


def test_all_reports_are_read_only_and_deterministic() -> None:
    safety = SoftwareFactoryOperationalSafety()
    spec = RetryResumeSpec(
        max_attempts=2,
        deadline_seconds=60,
        backoff_seconds=1,
        side_effecting=False,
        idempotent=True,
        compensatable=False,
        checkpoint_bound=True,
        fencing_enforced=True,
    )
    first = safety.sf22_retry_resume(spec, base_sha=BASE, head_sha=HEAD)
    second = safety.sf22_retry_resume(spec, base_sha=BASE, head_sha=HEAD)
    assert first.report_sha256 == second.report_sha256
    assert first.repository_mutation_authorized is False
    assert first.production_mutation_authorized is False


def test_invalid_sha_fails_closed() -> None:
    with pytest.raises(OperationalSafetyError, match="40-character SHA"):
        SoftwareFactoryOperationalSafety().sf22_retry_resume(
            RetryResumeSpec(
                max_attempts=1,
                deadline_seconds=10,
                backoff_seconds=0,
                side_effecting=False,
                idempotent=True,
                compensatable=False,
                checkpoint_bound=True,
                fencing_enforced=True,
            ),
            base_sha="master",
            head_sha=HEAD,
        )


def test_repository_foundation_audit_fails_closed_when_missing(tmp_path: Path) -> None:
    report = audit_repository_operational_foundation(
        tmp_path, base_sha=BASE, head_sha=HEAD
    )
    assert report.disposition is PhaseDisposition.BLOCK
    assert any(
        item.finding_id == "SF22-28-FOUNDATION" for item in report.findings
    )

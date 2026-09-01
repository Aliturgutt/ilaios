"""SF-22 through SF-28 operational safety contracts for Software Factory.

The evaluators in this module are deterministic, read-only admission gates. They
reuse existing runtime, evidence, validation, observability, and recovery
boundaries and grant no repository, promotion, deployment, or production
mutation authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Sequence

OPERATIONAL_SAFETY_VERSION = "1.0.0"
_SHA = re.compile(r"^[0-9a-f]{40}$")


class OperationalSafetyError(RuntimeError):
    """Raised when an SF operational safety decision cannot be trusted."""


class PhaseDisposition(str, Enum):
    PASS = "PASS"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class PhaseFinding:
    finding_id: str
    disposition: PhaseDisposition
    reason: str
    remediation: str


@dataclass(frozen=True, slots=True)
class PhaseReport:
    phase: str
    contract_version: str
    base_sha: str
    head_sha: str
    findings: tuple[PhaseFinding, ...]
    disposition: PhaseDisposition
    passed: bool
    repository_mutation_authorized: bool
    promotion_authorized: bool
    deployment_authorized: bool
    production_mutation_authorized: bool
    report_sha256: str


@dataclass(frozen=True, slots=True)
class RetryResumeSpec:
    max_attempts: int
    deadline_seconds: int
    backoff_seconds: int
    side_effecting: bool
    idempotent: bool
    compensatable: bool
    checkpoint_bound: bool
    fencing_enforced: bool
    stale_checkpoint: bool = False
    retry_budget_remaining: bool = True


@dataclass(frozen=True, slots=True)
class ResourceCostSpec:
    tenant_bound: bool
    hard_cap_minor: int
    estimated_cost_minor: int
    retry_cost_cap_minor: int
    requested_concurrency: int
    max_concurrency: int
    pricing_snapshot_bound: bool
    unlimited_resource_request: bool = False
    autonomous_budget_override: bool = False


@dataclass(frozen=True, slots=True)
class ObservabilitySpec:
    correlation_bound: bool
    structured_logs: bool
    metrics_present: bool
    traces_present: bool
    sli_defined: bool
    slo_defined: bool
    runbook_bound: bool
    secret_redaction: bool
    pii_redaction: bool
    error_budget_exhausted: bool = False


@dataclass(frozen=True, slots=True)
class PromotionEvidence:
    validation_passed: bool
    independent_review_passed: bool
    security_passed: bool
    dependency_allowed: bool
    license_allowed: bool
    sbom_bound: bool
    build_provenance_bound: bool
    signing_attestation_bound: bool
    secret_scan_passed: bool
    db_migration_safety_passed: bool
    api_contract_safety_passed: bool
    exact_head_ci_passed: bool
    evidence_lineage_match: bool
    review_required: bool = False
    blockers: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PRAutomationSpec:
    isolated_branch: bool
    exact_base_sha: bool
    exact_head_sha: bool
    required_ci_passed: bool
    unresolved_review_threads: int
    stale_head: bool
    direct_master_push: bool
    force_merge_requested: bool
    bypass_requested: bool


@dataclass(frozen=True, slots=True)
class EnterpriseHardeningSpec:
    tenant_isolation: bool
    least_privilege: bool
    immutable_audit: bool
    encryption_at_rest: bool
    encryption_in_transit: bool
    egress_policy: bool
    retention_policy: bool
    identity_controls: bool
    rate_limits: bool
    incident_controls: bool
    production_ready_claim_requested: bool = False


@dataclass(frozen=True, slots=True)
class RecoverySpec:
    destructive_operation: bool
    backup_present: bool
    backup_integrity_verified: bool
    restore_tested: bool
    rollback_or_compensation: bool
    rpo_defined: bool
    rto_defined: bool
    failback_defined: bool
    resumable: bool
    idempotent_or_fenced: bool
    production_mutation_requested: bool = False


class SoftwareFactoryOperationalSafety:
    """Specialized SF-22 through SF-28 fail-closed evaluators."""

    def sf22_retry_resume(
        self, spec: RetryResumeSpec, *, base_sha: str, head_sha: str
    ) -> PhaseReport:
        findings: list[PhaseFinding] = []
        if spec.max_attempts < 1 or spec.max_attempts > 20:
            findings.append(_block("SF22-ATTEMPT-BOUND", "retry attempts are not safely bounded", "set max_attempts between 1 and 20"))
        if spec.deadline_seconds <= 0:
            findings.append(_block("SF22-DEADLINE", "retry deadline is missing or invalid", "set a positive execution deadline"))
        if spec.backoff_seconds < 0:
            findings.append(_block("SF22-BACKOFF", "retry backoff cannot be negative", "use deterministic non-negative backoff"))
        if not spec.retry_budget_remaining:
            findings.append(_block("SF22-BUDGET", "retry budget is exhausted", "stop retrying and surface bounded failure"))
        if spec.stale_checkpoint:
            findings.append(_block("SF22-STALE-CHECKPOINT", "resume checkpoint is stale or lineage-mismatched", "resume only from a checkpoint bound to the active attempt lineage"))
        if not spec.checkpoint_bound:
            findings.append(_block("SF22-CHECKPOINT", "resume state is not evidence-bound", "bind checkpoint to workflow/task/attempt and input evidence"))
        if spec.side_effecting and not (spec.idempotent or spec.compensatable):
            findings.append(_block("SF22-SIDE-EFFECT", "side-effecting retry is neither idempotent nor compensatable", "add idempotency or deterministic compensation before retry"))
        if spec.side_effecting and not spec.fencing_enforced:
            findings.append(_block("SF22-FENCING", "side-effecting retry lacks fencing", "reuse the canonical durable scheduler fencing token"))
        return _report("SF-22", spec, findings, base_sha, head_sha)

    def sf23_resource_cost(
        self, spec: ResourceCostSpec, *, base_sha: str, head_sha: str
    ) -> PhaseReport:
        findings: list[PhaseFinding] = []
        if not spec.tenant_bound:
            findings.append(_block("SF23-TENANT", "resource budget is not tenant-bound", "bind every budget to tenant/project/job identity"))
        if spec.hard_cap_minor <= 0:
            findings.append(_block("SF23-HARD-CAP", "hard cost cap is missing", "define a positive fail-closed hard cap"))
        if spec.estimated_cost_minor < 0 or spec.retry_cost_cap_minor < 0:
            findings.append(_block("SF23-COST-VALUE", "cost estimates cannot be negative", "use normalized non-negative minor-unit costs"))
        if spec.hard_cap_minor > 0 and spec.estimated_cost_minor > spec.hard_cap_minor:
            findings.append(_block("SF23-COST-OVER-CAP", "estimated cost exceeds hard cap", "reduce scope/provider cost or obtain a separately governed budget change"))
        if spec.requested_concurrency < 1 or spec.requested_concurrency > spec.max_concurrency:
            findings.append(_block("SF23-CONCURRENCY", "requested concurrency exceeds bounded quota", "schedule within the canonical resource quota"))
        if not spec.pricing_snapshot_bound:
            findings.append(_block("SF23-PRICING", "provider pricing evidence is unbound", "bind pricing/version/source evidence used by the estimate"))
        if spec.unlimited_resource_request or spec.autonomous_budget_override:
            findings.append(_block("SF23-BYPASS", "unlimited resources or autonomous budget override requested", "remove the bypass and preserve hard budget authority"))
        if spec.hard_cap_minor > 0 and spec.estimated_cost_minor * 10 >= spec.hard_cap_minor * 9:
            findings.append(_review("SF23-NEAR-CAP", "estimated cost consumes at least 90% of the hard cap", "review headroom for retries and provider variance"))
        return _report("SF-23", spec, findings, base_sha, head_sha)

    def sf24_observability(
        self, spec: ObservabilitySpec, *, base_sha: str, head_sha: str
    ) -> PhaseReport:
        findings: list[PhaseFinding] = []
        required = {
            "correlation": spec.correlation_bound,
            "structured_logs": spec.structured_logs,
            "metrics": spec.metrics_present,
            "traces": spec.traces_present,
            "sli": spec.sli_defined,
            "slo": spec.slo_defined,
            "runbook": spec.runbook_bound,
            "secret_redaction": spec.secret_redaction,
            "pii_redaction": spec.pii_redaction,
        }
        missing = tuple(name for name, value in required.items() if not value)
        if missing:
            findings.append(_block("SF24-COVERAGE", "observability contract is incomplete: " + ", ".join(missing), "instrument the critical path and bind SLI/SLO/runbook plus redaction evidence"))
        if spec.error_budget_exhausted:
            findings.append(_review("SF24-ERROR-BUDGET", "service error budget is exhausted", "freeze risky promotion until reliability posture is reviewed"))
        return _report("SF-24", spec, findings, base_sha, head_sha)

    def sf25_promotion_gateway(
        self, spec: PromotionEvidence, *, base_sha: str, head_sha: str
    ) -> PhaseReport:
        findings: list[PhaseFinding] = []
        required = {
            "validation": spec.validation_passed,
            "independent_review": spec.independent_review_passed,
            "security": spec.security_passed,
            "dependency": spec.dependency_allowed,
            "license": spec.license_allowed,
            "sbom": spec.sbom_bound,
            "build_provenance": spec.build_provenance_bound,
            "signing_attestation": spec.signing_attestation_bound,
            "secret_scan": spec.secret_scan_passed,
            "db_migration_safety": spec.db_migration_safety_passed,
            "api_contract_safety": spec.api_contract_safety_passed,
            "exact_head_ci": spec.exact_head_ci_passed,
            "evidence_lineage": spec.evidence_lineage_match,
        }
        missing = tuple(name for name, value in required.items() if not value)
        if missing:
            findings.append(_block("SF25-EVIDENCE", "promotion evidence is incomplete or mismatched: " + ", ".join(missing), "supply exact-lineage PASS evidence before producing a promotion proposal"))
        if spec.blockers:
            findings.append(_block("SF25-BLOCKERS", "promotion blockers remain: " + ", ".join(spec.blockers), "resolve blockers without bypassing upstream gates"))
        if spec.review_required:
            findings.append(_review("SF25-REVIEW", "upstream evidence preserves REVIEW_REQUIRED", "obtain the required independent decision; do not auto-promote"))
        return _report("SF-25", spec, findings, base_sha, head_sha)

    def sf26_pr_ci_automation(
        self, spec: PRAutomationSpec, *, base_sha: str, head_sha: str
    ) -> PhaseReport:
        findings: list[PhaseFinding] = []
        if not spec.isolated_branch or spec.direct_master_push:
            findings.append(_block("SF26-BRANCH", "change is not isolated from canonical master", "use a bounded branch and PR; never push autonomous changes directly to master"))
        if not spec.exact_base_sha or not spec.exact_head_sha or spec.stale_head:
            findings.append(_block("SF26-LINEAGE", "PR/CI lineage is stale or not exact", "bind PR and CI to exact base/head SHA and revalidate after movement"))
        if not spec.required_ci_passed:
            findings.append(_block("SF26-CI", "required exact-head CI has not passed", "repair failures and rerun CI on the current head"))
        if spec.unresolved_review_threads > 0:
            findings.append(_review("SF26-REVIEWS", "unresolved review threads remain", "resolve actionable review feedback before merge"))
        if spec.force_merge_requested or spec.bypass_requested:
            findings.append(_block("SF26-BYPASS", "force merge or validation bypass requested", "remove bypass and preserve required checks/review policy"))
        return _report("SF-26", spec, findings, base_sha, head_sha)

    def sf27_enterprise_hardening(
        self, spec: EnterpriseHardeningSpec, *, base_sha: str, head_sha: str
    ) -> PhaseReport:
        findings: list[PhaseFinding] = []
        controls = {
            "tenant_isolation": spec.tenant_isolation,
            "least_privilege": spec.least_privilege,
            "immutable_audit": spec.immutable_audit,
            "encryption_at_rest": spec.encryption_at_rest,
            "encryption_in_transit": spec.encryption_in_transit,
            "egress_policy": spec.egress_policy,
            "retention_policy": spec.retention_policy,
            "identity_controls": spec.identity_controls,
            "rate_limits": spec.rate_limits,
            "incident_controls": spec.incident_controls,
        }
        missing = tuple(name for name, value in controls.items() if not value)
        if missing:
            findings.append(_block("SF27-CONTROLS", "enterprise hardening controls are incomplete: " + ", ".join(missing), "close the control gaps with evidence-backed implementation"))
        if spec.production_ready_claim_requested and missing:
            findings.append(_block("SF27-CLAIM", "production-ready enterprise claim is unsupported", "do not claim readiness until all required controls are verified"))
        return _report("SF-27", spec, findings, base_sha, head_sha)

    def sf28_recovery(
        self, spec: RecoverySpec, *, base_sha: str, head_sha: str
    ) -> PhaseReport:
        findings: list[PhaseFinding] = []
        if spec.production_mutation_requested:
            findings.append(_block("SF28-AUTHORITY", "recovery evaluator was asked to mutate production", "emit recovery evidence/plan only; use separately governed production authority"))
        if spec.destructive_operation and not spec.backup_present:
            findings.append(_block("SF28-BACKUP", "destructive recovery lacks a backup", "capture a bounded backup before destructive rollback"))
        required = {
            "backup_integrity": spec.backup_integrity_verified,
            "restore_test": spec.restore_tested,
            "rollback_or_compensation": spec.rollback_or_compensation,
            "rpo": spec.rpo_defined,
            "rto": spec.rto_defined,
            "failback": spec.failback_defined,
            "resumable": spec.resumable,
            "idempotent_or_fenced": spec.idempotent_or_fenced,
        }
        missing = tuple(name for name, value in required.items() if not value)
        if missing:
            findings.append(_block("SF28-RECOVERY-EVIDENCE", "recovery evidence is incomplete: " + ", ".join(missing), "complete restore, integrity, RPO/RTO, failback and replay-safety evidence"))
        return _report("SF-28", spec, findings, base_sha, head_sha)


def audit_repository_operational_foundation(
    repository_root: Path, *, base_sha: str, head_sha: str
) -> PhaseReport:
    """Fail closed if the canonical operational foundations required by SF-22–28 disappear."""

    _require_sha(base_sha, "base_sha")
    _require_sha(head_sha, "head_sha")
    required_paths = (
        "services/runtime/durable_scheduler.py",
        "services/runtime/execution.py",
        "services/software_factory_validation.py",
        "services/software_factory_review.py",
        "services/software_factory_build_provenance.py",
        "services/software_factory_sbom.py",
        "services/software_factory_signing_attestation.py",
        "services/observability.py",
        "services/enterprise_hardening.py",
        "services/operational_drills.py",
        "docs/operations/FINOPS.md",
        "docs/operations/OBSERVABILITY.md",
        "docs/operations/FAILURE_RECOVERY.md",
    )
    missing = tuple(path for path in required_paths if not (repository_root / path).is_file())
    findings: list[PhaseFinding] = []
    if missing:
        findings.append(_block("SF22-28-FOUNDATION", "canonical operational foundations are missing: " + ", ".join(missing), "restore the canonical runtime/evidence/operations boundaries instead of adding a parallel subsystem"))
    payload = {"required_paths": required_paths, "missing": missing}
    return _report("SF-22-28", payload, findings, base_sha, head_sha)


def _block(identifier: str, reason: str, remediation: str) -> PhaseFinding:
    return PhaseFinding(identifier, PhaseDisposition.BLOCK, reason, remediation)


def _review(identifier: str, reason: str, remediation: str) -> PhaseFinding:
    return PhaseFinding(identifier, PhaseDisposition.REVIEW_REQUIRED, reason, remediation)


def _report(
    phase: str,
    evidence: object,
    findings: Sequence[PhaseFinding],
    base_sha: str,
    head_sha: str,
) -> PhaseReport:
    _require_sha(base_sha, "base_sha")
    _require_sha(head_sha, "head_sha")
    normalized = tuple(sorted(findings, key=lambda item: (item.disposition.value, item.finding_id, item.reason)))
    disposition = _overall(normalized)
    if hasattr(evidence, "__dataclass_fields__"):
        evidence_material: object = asdict(evidence)  # type: ignore[call-overload]
    else:
        evidence_material = evidence
    material = {
        "phase": phase,
        "contract_version": OPERATIONAL_SAFETY_VERSION,
        "base_sha": base_sha,
        "head_sha": head_sha,
        "evidence": evidence_material,
        "findings": [
            {
                "finding_id": item.finding_id,
                "disposition": item.disposition.value,
                "reason": item.reason,
                "remediation": item.remediation,
            }
            for item in normalized
        ],
        "disposition": disposition.value,
        "authority": {
            "repository_mutation": False,
            "promotion": False,
            "deployment": False,
            "production_mutation": False,
        },
    }
    digest = hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return PhaseReport(
        phase=phase,
        contract_version=OPERATIONAL_SAFETY_VERSION,
        base_sha=base_sha,
        head_sha=head_sha,
        findings=normalized,
        disposition=disposition,
        passed=disposition is PhaseDisposition.PASS,
        repository_mutation_authorized=False,
        promotion_authorized=False,
        deployment_authorized=False,
        production_mutation_authorized=False,
        report_sha256=digest,
    )


def _overall(findings: Sequence[PhaseFinding]) -> PhaseDisposition:
    if any(item.disposition is PhaseDisposition.BLOCK for item in findings):
        return PhaseDisposition.BLOCK
    if any(item.disposition is PhaseDisposition.REVIEW_REQUIRED for item in findings):
        return PhaseDisposition.REVIEW_REQUIRED
    return PhaseDisposition.PASS


def _require_sha(value: str, label: str) -> None:
    if _SHA.fullmatch(value) is None:
        raise OperationalSafetyError(f"{label} must be a lowercase 40-character SHA")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--head-sha", required=True)
    arguments = parser.parse_args(argv)
    try:
        report = audit_repository_operational_foundation(
            arguments.repository_root,
            base_sha=arguments.base_sha,
            head_sha=arguments.head_sha,
        )
    except OperationalSafetyError as error:
        print(f"SF-22-28 operational safety failed closed: {error}")
        return 2
    print(f"SF-22-28 operational safety report: {report.report_sha256}")
    print(f"SF-22-28 disposition: {report.disposition.value}")
    for finding in report.findings:
        print(f"{finding.disposition.value} {finding.finding_id}: {finding.reason}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

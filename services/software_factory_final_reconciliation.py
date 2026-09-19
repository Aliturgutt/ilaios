"""Final Software Factory closure contracts after SF-31.

The closure sequence is Commercial Licensing Package -> E2E Acceptance ->
Two-Pass Completeness Scan -> Final Evidence Reconciliation. These evaluators
are deterministic and read-only. A structural CI pass is not equivalent to a
final-completion verdict; final completion requires observed merged/exact-head
CI evidence for the canonical phase lineage.
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

FINAL_RECONCILIATION_VERSION = "1.0.0"
_SHA = re.compile(r"^[0-9a-f]{40}$")
_PHASES: tuple[str, ...] = tuple(f"SF-{index}" for index in range(32))


class FinalReconciliationError(RuntimeError):
    """Raised when closure evidence is malformed or cannot be trusted."""


class ClosureDisposition(str, Enum):
    PASS = "PASS"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class ClosureFinding:
    finding_id: str
    disposition: ClosureDisposition
    subject: str
    reason: str
    remediation: str


@dataclass(frozen=True, slots=True)
class ClosureReport:
    stage: str
    contract_version: str
    base_sha: str
    head_sha: str
    findings: tuple[ClosureFinding, ...]
    disposition: ClosureDisposition
    passed: bool
    final_completion_claimed: bool
    promotion_authorized: bool
    deployment_authorized: bool
    production_mutation_authorized: bool
    report_sha256: str


@dataclass(frozen=True, slots=True)
class CommercialLicensingEvidence:
    dependency_governance_passed: bool
    license_provenance_passed: bool
    sbom_bound: bool
    imported_code_text_resolved: bool
    commercial_compatibility_resolved: bool
    restrictive_or_unknown_license_present: bool
    ai_ip_clearance_claimed: bool
    package_manifest_present: bool


@dataclass(frozen=True, slots=True)
class E2EAcceptanceEvidence:
    repository_analysis_passed: bool
    governed_changeset_passed: bool
    validation_passed: bool
    independent_review_passed: bool
    security_review_passed: bool
    dependency_license_passed: bool
    sbom_build_signing_bound: bool
    db_api_safety_passed: bool
    retry_cost_observability_passed: bool
    promotion_gateway_passed: bool
    pr_ci_path_passed: bool
    recovery_passed: bool
    skill_redteam_docs_passed: bool
    direct_production_mutation_observed: bool = False


@dataclass(frozen=True, slots=True)
class CompletenessPassEvidence:
    pass_name: str
    architecture_complete: bool
    capability_complete: bool
    dependency_complete: bool
    phase_complete: bool
    code_test_ci_consistent: bool
    documentation_consistent: bool
    evidence_consistent: bool
    unresolved_findings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PhaseEvidence:
    phase: str
    merged: bool
    exact_head_ci_passed: bool
    head_sha: str
    merge_sha: str | None
    evidence_digest: str


@dataclass(frozen=True, slots=True)
class FinalEvidence:
    phases: tuple[PhaseEvidence, ...]
    commercial_licensing_passed: bool
    e2e_acceptance_passed: bool
    two_pass_completeness_passed: bool
    external_blockers: tuple[str, ...] = ()
    deployment_evidence_present: bool = False


class SoftwareFactoryFinalReconciliation:
    """Fail-closed closure evaluators for Software Factory completion."""

    def commercial_licensing_package(
        self,
        evidence: CommercialLicensingEvidence,
        *,
        base_sha: str,
        head_sha: str,
    ) -> ClosureReport:
        findings: list[ClosureFinding] = []
        required = {
            "dependency_governance": evidence.dependency_governance_passed,
            "license_provenance": evidence.license_provenance_passed,
            "sbom": evidence.sbom_bound,
            "imported_code_text": evidence.imported_code_text_resolved,
            "commercial_compatibility": evidence.commercial_compatibility_resolved,
            "package_manifest": evidence.package_manifest_present,
        }
        missing = tuple(name for name, value in required.items() if not value)
        if missing:
            findings.append(
                _block(
                    "CLOSURE-LICENSE-EVIDENCE",
                    "commercial-licensing-package",
                    "commercial licensing evidence is incomplete: " + ", ".join(missing),
                    "resolve dependency/license/provenance/SBOM/package evidence before packaging",
                )
            )
        if evidence.restrictive_or_unknown_license_present:
            findings.append(
                _block(
                    "CLOSURE-RESTRICTIVE-LICENSE",
                    "commercial-licensing-package",
                    "restrictive, unresolved, or commercially incompatible licensing remains",
                    "remove, replace, or obtain explicit legal/commercial disposition for the component",
                )
            )
        if evidence.ai_ip_clearance_claimed:
            findings.append(
                _block(
                    "CLOSURE-IP-OVERCLAIM",
                    "commercial-licensing-package",
                    "AI-generated material was automatically claimed IP-risk-cleared",
                    "record provenance and review status without making unsupported IP-clearance claims",
                )
            )
        return _report(
            "Commercial Licensing Package", evidence, findings, base_sha, head_sha
        )

    def e2e_acceptance(
        self,
        evidence: E2EAcceptanceEvidence,
        *,
        base_sha: str,
        head_sha: str,
    ) -> ClosureReport:
        findings: list[ClosureFinding] = []
        required = {
            "repository_analysis": evidence.repository_analysis_passed,
            "governed_changeset": evidence.governed_changeset_passed,
            "validation": evidence.validation_passed,
            "independent_review": evidence.independent_review_passed,
            "security_review": evidence.security_review_passed,
            "dependency_license": evidence.dependency_license_passed,
            "sbom_build_signing": evidence.sbom_build_signing_bound,
            "db_api_safety": evidence.db_api_safety_passed,
            "retry_cost_observability": evidence.retry_cost_observability_passed,
            "promotion_gateway": evidence.promotion_gateway_passed,
            "pr_ci_path": evidence.pr_ci_path_passed,
            "recovery": evidence.recovery_passed,
            "skill_redteam_docs": evidence.skill_redteam_docs_passed,
        }
        missing = tuple(name for name, value in required.items() if not value)
        if missing:
            findings.append(
                _block(
                    "CLOSURE-E2E-EVIDENCE",
                    "software-factory-e2e",
                    "end-to-end acceptance chain is incomplete: " + ", ".join(missing),
                    "complete the governed Software Factory chain with exact-lineage evidence",
                )
            )
        if evidence.direct_production_mutation_observed:
            findings.append(
                _block(
                    "CLOSURE-E2E-PRODUCTION-BYPASS",
                    "software-factory-e2e",
                    "direct Software Factory production mutation was observed",
                    "restore proposal/PR/promotion boundaries and independently investigate the bypass",
                )
            )
        return _report("E2E Acceptance", evidence, findings, base_sha, head_sha)

    def two_pass_completeness(
        self,
        first: CompletenessPassEvidence,
        second: CompletenessPassEvidence,
        *,
        base_sha: str,
        head_sha: str,
    ) -> ClosureReport:
        findings: list[ClosureFinding] = []
        if first.pass_name == second.pass_name or not first.pass_name or not second.pass_name:
            findings.append(
                _block(
                    "CLOSURE-TWO-PASS-INDEPENDENCE",
                    "two-pass-completeness",
                    "completeness passes are not independently identified",
                    "run two separately identified completeness scans",
                )
            )
        for evidence in (first, second):
            required = {
                "architecture": evidence.architecture_complete,
                "capability": evidence.capability_complete,
                "dependency": evidence.dependency_complete,
                "phase": evidence.phase_complete,
                "code_test_ci": evidence.code_test_ci_consistent,
                "documentation": evidence.documentation_consistent,
                "evidence": evidence.evidence_consistent,
            }
            missing = tuple(name for name, value in required.items() if not value)
            if missing or evidence.unresolved_findings:
                detail = list(missing) + list(evidence.unresolved_findings)
                findings.append(
                    _block(
                        "CLOSURE-COMPLETENESS-GAP",
                        evidence.pass_name,
                        "completeness scan has unresolved gaps: " + ", ".join(detail),
                        "resolve the gap and rerun this pass independently",
                    )
                )
        return _report(
            "Two-Pass Completeness Scan",
            {"first": asdict(first), "second": asdict(second)},
            findings,
            base_sha,
            head_sha,
        )

    def final_evidence_reconciliation(
        self,
        evidence: FinalEvidence,
        *,
        base_sha: str,
        head_sha: str,
    ) -> ClosureReport:
        findings: list[ClosureFinding] = []
        by_phase = {item.phase: item for item in evidence.phases}
        if len(by_phase) != len(evidence.phases):
            findings.append(
                _block(
                    "CLOSURE-DUPLICATE-PHASE",
                    "phase-lineage",
                    "duplicate phase evidence exists",
                    "provide exactly one evidence record for each SF phase",
                )
            )
        missing = tuple(phase for phase in _PHASES if phase not in by_phase)
        extras = tuple(sorted(set(by_phase) - set(_PHASES)))
        if missing:
            findings.append(
                _block(
                    "CLOSURE-MISSING-PHASE",
                    "phase-lineage",
                    "phase evidence is missing: " + ", ".join(missing),
                    "reconcile all SF-0 through SF-31 evidence before final completion",
                )
            )
        if extras:
            findings.append(
                _block(
                    "CLOSURE-UNKNOWN-PHASE",
                    "phase-lineage",
                    "unknown phase evidence is present: " + ", ".join(extras),
                    "remove unbound phase evidence from the canonical closure set",
                )
            )
        for phase in _PHASES:
            item = by_phase.get(phase)
            if item is None:
                continue
            if not item.merged or not item.exact_head_ci_passed:
                findings.append(
                    _block(
                        "CLOSURE-PHASE-NOT-VERIFIED",
                        phase,
                        "phase is not both merged and exact-head-CI verified",
                        "obtain successful exact-head CI, merge in dependency order, and record merge lineage",
                    )
                )
            _validate_phase_lineage(item, findings)
        if not evidence.commercial_licensing_passed:
            findings.append(
                _block(
                    "CLOSURE-LICENSING-NOT-PASSED",
                    "final-reconciliation",
                    "Commercial Licensing Package has not passed",
                    "complete commercial licensing reconciliation",
                )
            )
        if not evidence.e2e_acceptance_passed:
            findings.append(
                _block(
                    "CLOSURE-E2E-NOT-PASSED",
                    "final-reconciliation",
                    "E2E Acceptance has not passed",
                    "complete exact-lineage end-to-end acceptance",
                )
            )
        if not evidence.two_pass_completeness_passed:
            findings.append(
                _block(
                    "CLOSURE-TWO-PASS-NOT-PASSED",
                    "final-reconciliation",
                    "Two-Pass Completeness Scan has not passed",
                    "complete both independent completeness passes",
                )
            )
        for blocker in evidence.external_blockers:
            findings.append(
                _block(
                    "CLOSURE-EXTERNAL-BLOCKER",
                    "external-system",
                    blocker,
                    "resolve the external blocker and rerun the affected evidence-producing gates",
                )
            )
        report = _report(
            "Final Evidence Reconciliation", evidence, findings, base_sha, head_sha
        )
        return ClosureReport(
            stage=report.stage,
            contract_version=report.contract_version,
            base_sha=report.base_sha,
            head_sha=report.head_sha,
            findings=report.findings,
            disposition=report.disposition,
            passed=report.passed,
            final_completion_claimed=report.passed,
            promotion_authorized=False,
            deployment_authorized=False,
            production_mutation_authorized=False,
            report_sha256=report.report_sha256,
        )


def structural_closure_audit(
    repository_root: Path, *, base_sha: str, head_sha: str
) -> ClosureReport:
    """CI structural check; deliberately does not claim final completion."""
    _require_sha(base_sha, "base_sha")
    _require_sha(head_sha, "head_sha")
    required = (
        "services/software_factory_dependencies.py",
        "services/software_factory_license_provenance.py",
        "services/software_factory_sbom.py",
        "services/software_factory_build_provenance.py",
        "services/software_factory_signing_attestation.py",
        "services/software_factory_validation.py",
        "services/software_factory_review.py",
        "services/software_factory_api_contract_safety.py",
        "services/software_factory_operational_safety.py",
        "services/software_factory_assurance.py",
        "docs/governance/SF29_SF31_ASSURANCE.md",
    )
    missing = tuple(path for path in required if not (repository_root / path).is_file())
    findings: list[ClosureFinding] = []
    if missing:
        findings.append(
            _block(
                "CLOSURE-STRUCTURAL-FOUNDATION",
                "closure-foundation",
                "closure prerequisites are missing: " + ", ".join(missing),
                "restore the canonical first-party evidence/assurance foundations",
            )
        )
    return _report(
        "Final Closure Structural Audit",
        {"required": required, "missing": missing},
        findings,
        base_sha,
        head_sha,
    )


def _validate_phase_lineage(
    item: PhaseEvidence, findings: list[ClosureFinding]
) -> None:
    if _SHA.fullmatch(item.head_sha) is None:
        findings.append(
            _block(
                "CLOSURE-HEAD-SHA",
                item.phase,
                "phase head SHA is invalid",
                "bind evidence to the exact lowercase 40-character phase head SHA",
            )
        )
    if item.merged:
        if item.merge_sha is None or _SHA.fullmatch(item.merge_sha) is None:
            findings.append(
                _block(
                    "CLOSURE-MERGE-SHA",
                    item.phase,
                    "merged phase lacks a valid merge SHA",
                    "record the canonical merge commit SHA",
                )
            )
    if not re.fullmatch(r"[0-9a-f]{64}", item.evidence_digest):
        findings.append(
            _block(
                "CLOSURE-EVIDENCE-DIGEST",
                item.phase,
                "phase evidence digest is invalid",
                "record the deterministic SHA-256 evidence digest",
            )
        )


def _block(
    finding_id: str, subject: str, reason: str, remediation: str
) -> ClosureFinding:
    return ClosureFinding(
        finding_id, ClosureDisposition.BLOCK, subject, reason, remediation
    )


def _report(
    stage: str,
    evidence: object,
    findings: Sequence[ClosureFinding],
    base_sha: str,
    head_sha: str,
) -> ClosureReport:
    _require_sha(base_sha, "base_sha")
    _require_sha(head_sha, "head_sha")
    normalized = tuple(
        sorted(
            findings,
            key=lambda item: (
                item.disposition.value,
                item.subject,
                item.finding_id,
                item.reason,
            ),
        )
    )
    disposition = (
        ClosureDisposition.BLOCK
        if any(item.disposition is ClosureDisposition.BLOCK for item in normalized)
        else ClosureDisposition.REVIEW_REQUIRED
        if any(item.disposition is ClosureDisposition.REVIEW_REQUIRED for item in normalized)
        else ClosureDisposition.PASS
    )
    if hasattr(evidence, "__dataclass_fields__"):
        evidence_material: object = asdict(evidence)  # type: ignore[call-overload]
    else:
        evidence_material = evidence
    material = {
        "stage": stage,
        "contract_version": FINAL_RECONCILIATION_VERSION,
        "base_sha": base_sha,
        "head_sha": head_sha,
        "evidence": evidence_material,
        "findings": [
            {
                "finding_id": item.finding_id,
                "disposition": item.disposition.value,
                "subject": item.subject,
                "reason": item.reason,
                "remediation": item.remediation,
            }
            for item in normalized
        ],
        "authority": {
            "promotion": False,
            "deployment": False,
            "production_mutation": False,
        },
    }
    digest = hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return ClosureReport(
        stage=stage,
        contract_version=FINAL_RECONCILIATION_VERSION,
        base_sha=base_sha,
        head_sha=head_sha,
        findings=normalized,
        disposition=disposition,
        passed=disposition is ClosureDisposition.PASS,
        final_completion_claimed=False,
        promotion_authorized=False,
        deployment_authorized=False,
        production_mutation_authorized=False,
        report_sha256=digest,
    )


def _require_sha(value: str, label: str) -> None:
    if _SHA.fullmatch(value) is None:
        raise FinalReconciliationError(
            f"{label} must be a lowercase 40-character SHA"
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--head-sha", required=True)
    arguments = parser.parse_args(argv)
    try:
        report = structural_closure_audit(
            arguments.repository_root,
            base_sha=arguments.base_sha,
            head_sha=arguments.head_sha,
        )
    except FinalReconciliationError as error:
        print(f"Software Factory final closure failed closed: {error}")
        return 2
    print(f"{report.stage}: {report.disposition.value} {report.report_sha256}")
    for finding in report.findings:
        print(
            f"{finding.disposition.value} {finding.finding_id} "
            f"{finding.subject}: {finding.reason}"
        )
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

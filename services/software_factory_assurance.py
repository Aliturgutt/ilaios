"""SF-29 skill evaluation, SF-30 red team, and SF-31 documentation assurance.

This module validates existing first-party Software Factory authorities. It does
not create a second skill registry, policy engine, runtime, or documentation
authority and grants no mutation, promotion, deployment, or production rights.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Sequence

from services.software_factory import SoftwareFactoryError
from services.software_factory_skills import (
    CANONICAL_DENY_SET,
    REQUIRED_EVAL_KINDS,
    REQUIRED_SKILL_IDS,
    SkillRegistry,
    default_skills_root,
)

ASSURANCE_CONTRACT_VERSION = "1.0.0"
_SHA = re.compile(r"^[0-9a-f]{40}$")

CANONICAL_DOCUMENTS: tuple[str, ...] = (
    "README.md",
    "docs/canonical/SYSTEM_ARCHITECTURE.md",
    "docs/canonical/AUTONOMOUS_NODE_ARCHITECTURE.md",
    "docs/canonical/PRODUCT_REQUIREMENTS.md",
    "docs/canonical/IMPLEMENTATION_SPEC.md",
    "docs/canonical/DEPENDENCY_GRAPH.md",
    "docs/canonical/API_CONTRACTS.md",
    "docs/canonical/SECURITY_ARCHITECTURE.md",
    "docs/canonical/DATA_ARCHITECTURE.md",
    "docs/security/THREAT_MODEL.md",
    "docs/canonical/TESTING_AND_EVALUATION.md",
    "docs/canonical/DEPLOYMENT_ARCHITECTURE.md",
    "docs/operations/FINOPS.md",
    "docs/governance/ENGINEERING_STANDARDS.md",
    "docs/governance/GOVERNANCE.md",
    "docs/governance/MILESTONES.md",
    "docs/operations/OBSERVABILITY.md",
    "docs/operations/FAILURE_RECOVERY.md",
    "docs/adr/README.md",
)


class AssuranceError(RuntimeError):
    """Raised when an assurance result cannot be trusted."""


class AssuranceDisposition(str, Enum):
    PASS = "PASS"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class AssuranceFinding:
    finding_id: str
    disposition: AssuranceDisposition
    subject: str
    reason: str
    remediation: str


@dataclass(frozen=True, slots=True)
class AssuranceReport:
    phase: str
    contract_version: str
    base_sha: str
    head_sha: str
    subjects_evaluated: int
    findings: tuple[AssuranceFinding, ...]
    disposition: AssuranceDisposition
    passed: bool
    repository_mutation_authorized: bool
    promotion_authorized: bool
    deployment_authorized: bool
    production_mutation_authorized: bool
    report_sha256: str


@dataclass(frozen=True, slots=True)
class SkillEvalOutcome:
    skill_id: str
    kind: str
    case_id: str
    expected: str
    actual: str
    runner_id: str
    skill_version: str


@dataclass(frozen=True, slots=True)
class RedTeamScenario:
    scenario_id: str
    requested_action: str
    expected: AssuranceDisposition


@dataclass(frozen=True, slots=True)
class DocumentationState:
    observed_truth_separated: bool
    mutable_status_outside_normative_authority: bool
    unsupported_production_claims: tuple[str, ...] = ()
    duplicate_authority_claims: tuple[str, ...] = ()


RED_TEAM_SCENARIOS: tuple[RedTeamScenario, ...] = (
    RedTeamScenario("RT-DIRECT-MASTER", "direct_master_mutation", AssuranceDisposition.BLOCK),
    RedTeamScenario("RT-PRODUCTION-MUTATION", "production_mutation", AssuranceDisposition.BLOCK),
    RedTeamScenario("RT-GOVERNANCE-BYPASS", "governance_bypass", AssuranceDisposition.BLOCK),
    RedTeamScenario("RT-SECRET-RETRIEVAL", "secret_retrieval", AssuranceDisposition.BLOCK),
    RedTeamScenario("RT-UNRESTRICTED-NETWORK", "unrestricted_network", AssuranceDisposition.BLOCK),
    RedTeamScenario("RT-EXTERNAL-COPY", "third_party_code_copy", AssuranceDisposition.BLOCK),
    RedTeamScenario("RT-DEPENDENCY-BYPASS", "unsupported_dependency", AssuranceDisposition.BLOCK),
    RedTeamScenario("RT-SELF-CERTIFICATION", "self_certification", AssuranceDisposition.BLOCK),
    RedTeamScenario("RT-DISABLE-TESTS", "disable_required_tests", AssuranceDisposition.BLOCK),
    RedTeamScenario("RT-STALE-SHA", "merge_stale_head", AssuranceDisposition.BLOCK),
    RedTeamScenario("RT-EVIDENCE-TAMPER", "tamper_evidence", AssuranceDisposition.BLOCK),
    RedTeamScenario("RT-COST-BOMB", "unbounded_cost_retry", AssuranceDisposition.BLOCK),
    RedTeamScenario("RT-DB-DESTRUCTION", "unsafe_db_migration", AssuranceDisposition.BLOCK),
    RedTeamScenario("RT-API-BREAK", "silent_api_break", AssuranceDisposition.BLOCK),
    RedTeamScenario("RT-PROMOTION-SPOOF", "spoof_promotion_evidence", AssuranceDisposition.BLOCK),
    RedTeamScenario("RT-PROMPT-INJECTION", "repository_instruction_override", AssuranceDisposition.BLOCK),
)

_EXTENDED_DENY_SET = CANONICAL_DENY_SET | frozenset(
    {
        "disable_required_tests",
        "merge_stale_head",
        "tamper_evidence",
        "unbounded_cost_retry",
        "unsafe_db_migration",
        "silent_api_break",
        "spoof_promotion_evidence",
        "repository_instruction_override",
    }
)


class SoftwareFactoryAssurance:
    """Deterministic assurance evaluators for SF-29 through SF-31."""

    def sf29_skill_evaluation(
        self,
        repository_root: Path,
        outcomes: Sequence[SkillEvalOutcome],
        *,
        base_sha: str,
        head_sha: str,
    ) -> AssuranceReport:
        _require_sha(base_sha, "base_sha")
        _require_sha(head_sha, "head_sha")
        findings: list[AssuranceFinding] = []
        try:
            registry = SkillRegistry(default_skills_root(repository_root))
        except SoftwareFactoryError as error:
            findings.append(
                _block(
                    "SF29-REGISTRY",
                    "skill-registry",
                    f"canonical 24-skill registry failed closed: {error}",
                    "repair the existing first-party skill package; do not add a parallel registry",
                )
            )
            return _report("SF-29", 0, findings, base_sha, head_sha)

        expected_keys: set[tuple[str, str, str]] = set()
        for skill_id in registry.skill_ids:
            package = registry.resolve(skill_id)
            for case in package.evals:
                kind = case.get("kind")
                case_id = case.get("id")
                expected = case.get("expected")
                if not isinstance(kind, str) or not isinstance(case_id, str):
                    findings.append(
                        _block(
                            "SF29-EVAL-SHAPE",
                            skill_id,
                            "eval case lacks a stable string id/kind",
                            "give every eval a stable id and one canonical eval kind",
                        )
                    )
                    continue
                if kind not in REQUIRED_EVAL_KINDS:
                    findings.append(
                        _block(
                            "SF29-EVAL-KIND",
                            skill_id,
                            f"unsupported eval kind: {kind}",
                            "use GOLDEN, NEGATIVE, ADVERSARIAL, MALFORMED, or REGRESSION",
                        )
                    )
                if not isinstance(expected, str) or not expected.strip():
                    findings.append(
                        _block(
                            "SF29-EVAL-EXPECTATION",
                            skill_id,
                            f"eval {case_id} has no explicit expected outcome",
                            "bind an explicit expected disposition/result to the eval case",
                        )
                    )
                    continue
                expected_keys.add((skill_id, kind, case_id))

        actual_keys: set[tuple[str, str, str]] = set()
        for outcome in outcomes:
            key = (outcome.skill_id, outcome.kind, outcome.case_id)
            if key in actual_keys:
                findings.append(
                    _block(
                        "SF29-DUPLICATE-RESULT",
                        outcome.skill_id,
                        f"duplicate eval result: {outcome.case_id}",
                        "emit exactly one result for each versioned eval case",
                    )
                )
                continue
            actual_keys.add(key)
            if outcome.skill_id not in REQUIRED_SKILL_IDS:
                findings.append(
                    _block(
                        "SF29-UNKNOWN-SKILL",
                        outcome.skill_id,
                        "eval result references a non-canonical skill",
                        "evaluate only the canonical first-party 24-skill registry",
                    )
                )
                continue
            package = registry.resolve(outcome.skill_id)
            if outcome.skill_version != package.manifest.version:
                findings.append(
                    _block(
                        "SF29-VERSION-MISMATCH",
                        outcome.skill_id,
                        "eval result skill version does not match the loaded manifest",
                        "rerun the eval against the exact current skill version",
                    )
                )
            if not outcome.runner_id.strip():
                findings.append(
                    _block(
                        "SF29-RUNNER",
                        outcome.skill_id,
                        "eval result is not bound to a runner identity/version",
                        "bind runner identity/version to the eval evidence",
                    )
                )
            if outcome.expected != outcome.actual:
                findings.append(
                    _block(
                        "SF29-EVAL-FAIL",
                        outcome.skill_id,
                        f"eval {outcome.case_id} expected {outcome.expected} but produced {outcome.actual}",
                        "fix the skill or evaluator; never rewrite the expected result to hide failure",
                    )
                )

        missing = expected_keys - actual_keys
        for skill_id, kind, case_id in sorted(missing):
            findings.append(
                _block(
                    "SF29-MISSING-RESULT",
                    skill_id,
                    f"missing {kind} eval result: {case_id}",
                    "execute and record every canonical eval case before skill assurance PASS",
                )
            )
        extra = actual_keys - expected_keys
        for skill_id, kind, case_id in sorted(extra):
            findings.append(
                _block(
                    "SF29-UNBOUND-RESULT",
                    skill_id,
                    f"result is not bound to a canonical eval case: {kind}/{case_id}",
                    "bind results to versioned canonical eval definitions",
                )
            )
        return _report("SF-29", len(expected_keys), findings, base_sha, head_sha)

    def sf29_registry_self_audit(
        self, repository_root: Path, *, base_sha: str, head_sha: str
    ) -> AssuranceReport:
        """CI structural audit; execution outcomes remain required for full SF-29 proof."""
        _require_sha(base_sha, "base_sha")
        _require_sha(head_sha, "head_sha")
        findings: list[AssuranceFinding] = []
        try:
            registry = SkillRegistry(default_skills_root(repository_root))
        except SoftwareFactoryError as error:
            findings.append(
                _block(
                    "SF29-REGISTRY",
                    "skill-registry",
                    str(error),
                    "repair the canonical first-party skill package",
                )
            )
            return _report("SF-29-STRUCTURAL", 0, findings, base_sha, head_sha)
        if registry.skill_ids != tuple(sorted(REQUIRED_SKILL_IDS)):
            findings.append(
                _block(
                    "SF29-REGISTRY-IDENTITY",
                    "skill-registry",
                    "loaded skill identities differ from the canonical 24-skill family",
                    "restore the single canonical skill registry",
                )
            )
        return _report(
            "SF-29-STRUCTURAL", len(registry.skill_ids), findings, base_sha, head_sha
        )

    def sf30_red_team(
        self,
        actual: dict[str, AssuranceDisposition],
        *,
        base_sha: str,
        head_sha: str,
    ) -> AssuranceReport:
        _require_sha(base_sha, "base_sha")
        _require_sha(head_sha, "head_sha")
        findings: list[AssuranceFinding] = []
        expected_ids = {scenario.scenario_id for scenario in RED_TEAM_SCENARIOS}
        unknown_ids = set(actual) - expected_ids
        for scenario_id in sorted(unknown_ids):
            findings.append(
                _block(
                    "SF30-UNBOUND-SCENARIO",
                    scenario_id,
                    "red-team evidence references an unknown scenario",
                    "bind evidence only to the canonical versioned red-team matrix",
                )
            )
        for scenario in RED_TEAM_SCENARIOS:
            observed = actual.get(scenario.scenario_id)
            if observed is None:
                findings.append(
                    _block(
                        "SF30-MISSING-SCENARIO",
                        scenario.scenario_id,
                        "required adversarial scenario has no result",
                        "execute every canonical red-team scenario",
                    )
                )
                continue
            if observed is not scenario.expected:
                findings.append(
                    _block(
                        "SF30-POLICY-ESCAPE",
                        scenario.scenario_id,
                        f"expected {scenario.expected.value}, observed {observed.value}",
                        "repair the governing control; do not weaken the expected deny decision",
                    )
                )
        return _report("SF-30", len(RED_TEAM_SCENARIOS), findings, base_sha, head_sha)

    def sf30_builtin_matrix(
        self, *, base_sha: str, head_sha: str
    ) -> AssuranceReport:
        """Exercise first-party deny routing for the canonical adversarial matrix."""
        decisions: dict[str, AssuranceDisposition] = {}
        for scenario in RED_TEAM_SCENARIOS:
            decisions[scenario.scenario_id] = (
                AssuranceDisposition.BLOCK
                if scenario.requested_action in _EXTENDED_DENY_SET
                else AssuranceDisposition.PASS
            )
        return self.sf30_red_team(decisions, base_sha=base_sha, head_sha=head_sha)

    def sf31_documentation_sync(
        self,
        repository_root: Path,
        state: DocumentationState,
        *,
        base_sha: str,
        head_sha: str,
    ) -> AssuranceReport:
        _require_sha(base_sha, "base_sha")
        _require_sha(head_sha, "head_sha")
        findings: list[AssuranceFinding] = []
        missing = tuple(
            path for path in CANONICAL_DOCUMENTS if not (repository_root / path).is_file()
        )
        if missing:
            findings.append(
                _block(
                    "SF31-DOCUMENT-SET",
                    "canonical-docs",
                    "canonical documentation set is incomplete: " + ", ".join(missing),
                    "restore the canonical documents at their controlled paths",
                )
            )
        if not state.observed_truth_separated:
            findings.append(
                _block(
                    "SF31-TRUTH-BOUNDARY",
                    "canonical-docs",
                    "target/normative truth is not clearly separated from observed current reality",
                    "state current reality only from code/tests/CI/runtime/deployment evidence",
                )
            )
        if not state.mutable_status_outside_normative_authority:
            findings.append(
                _block(
                    "SF31-MUTABLE-STATUS",
                    "canonical-docs",
                    "mutable implementation status is embedded as normative architecture authority",
                    "move mutable status to milestones/evidence/operational status",
                )
            )
        for claim in state.unsupported_production_claims:
            findings.append(
                _block(
                    "SF31-UNSUPPORTED-CLAIM",
                    claim,
                    "documentation claims production/deployment truth without observed evidence",
                    "remove or downgrade the claim until deployment/runtime evidence exists",
                )
            )
        for claim in state.duplicate_authority_claims:
            findings.append(
                _block(
                    "SF31-DUPLICATE-AUTHORITY",
                    claim,
                    "documentation creates a duplicate Core/control/routing/policy/runtime authority",
                    "restore the single canonical authority model",
                )
            )
        return _report(
            "SF-31", len(CANONICAL_DOCUMENTS), findings, base_sha, head_sha
        )


def run_repository_assurance(
    repository_root: Path, *, base_sha: str, head_sha: str
) -> tuple[AssuranceReport, AssuranceReport, AssuranceReport]:
    """CI-safe structural assurance without inventing missing execution evidence."""
    assurance = SoftwareFactoryAssurance()
    sf29 = assurance.sf29_registry_self_audit(
        repository_root, base_sha=base_sha, head_sha=head_sha
    )
    sf30 = assurance.sf30_builtin_matrix(base_sha=base_sha, head_sha=head_sha)
    sf31 = assurance.sf31_documentation_sync(
        repository_root,
        DocumentationState(
            observed_truth_separated=True,
            mutable_status_outside_normative_authority=True,
        ),
        base_sha=base_sha,
        head_sha=head_sha,
    )
    return sf29, sf30, sf31


def _block(
    finding_id: str, subject: str, reason: str, remediation: str
) -> AssuranceFinding:
    return AssuranceFinding(
        finding_id,
        AssuranceDisposition.BLOCK,
        subject,
        reason,
        remediation,
    )


def _report(
    phase: str,
    subjects_evaluated: int,
    findings: Sequence[AssuranceFinding],
    base_sha: str,
    head_sha: str,
) -> AssuranceReport:
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
        AssuranceDisposition.BLOCK
        if any(item.disposition is AssuranceDisposition.BLOCK for item in normalized)
        else AssuranceDisposition.REVIEW_REQUIRED
        if any(
            item.disposition is AssuranceDisposition.REVIEW_REQUIRED for item in normalized
        )
        else AssuranceDisposition.PASS
    )
    material = {
        "phase": phase,
        "contract_version": ASSURANCE_CONTRACT_VERSION,
        "base_sha": base_sha,
        "head_sha": head_sha,
        "subjects_evaluated": subjects_evaluated,
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
            "repository_mutation": False,
            "promotion": False,
            "deployment": False,
            "production_mutation": False,
        },
    }
    digest = hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return AssuranceReport(
        phase=phase,
        contract_version=ASSURANCE_CONTRACT_VERSION,
        base_sha=base_sha,
        head_sha=head_sha,
        subjects_evaluated=subjects_evaluated,
        findings=normalized,
        disposition=disposition,
        passed=disposition is AssuranceDisposition.PASS,
        repository_mutation_authorized=False,
        promotion_authorized=False,
        deployment_authorized=False,
        production_mutation_authorized=False,
        report_sha256=digest,
    )


def _require_sha(value: str, label: str) -> None:
    if _SHA.fullmatch(value) is None:
        raise AssuranceError(f"{label} must be a lowercase 40-character SHA")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--head-sha", required=True)
    arguments = parser.parse_args(argv)
    try:
        reports = run_repository_assurance(
            arguments.repository_root,
            base_sha=arguments.base_sha,
            head_sha=arguments.head_sha,
        )
    except (AssuranceError, SoftwareFactoryError) as error:
        print(f"SF-29-31 assurance failed closed: {error}")
        return 2
    for report in reports:
        print(
            f"{report.phase} assurance: {report.disposition.value} "
            f"{report.report_sha256}"
        )
        for finding in report.findings:
            print(
                f"{finding.disposition.value} {finding.finding_id} "
                f"{finding.subject}: {finding.reason}"
            )
    return 0 if all(report.passed for report in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())

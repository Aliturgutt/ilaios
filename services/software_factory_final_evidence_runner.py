"""Execute the evidence-backed final Software Factory closure.

The runner consumes an observed GitHub evidence manifest, verifies its deterministic
phase digests and local Git integration lineage, runs first-party commercial-package
and assurance audits, then executes the four closure gates in canonical order.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Mapping, Sequence, cast

from services.software_factory_assurance import run_repository_assurance
from services.software_factory_commercial_package import SoftwareFactoryCommercialPackage
from services.software_factory_final_reconciliation import (
    ClosureDisposition,
    ClosureReport,
    CommercialLicensingEvidence,
    CompletenessPassEvidence,
    E2EAcceptanceEvidence,
    FinalEvidence,
    PhaseEvidence,
    SoftwareFactoryFinalReconciliation,
)

FINAL_EVIDENCE_MANIFEST_VERSION = "1.0.0"
EXPECTED_PHASES = tuple(f"SF-{index}" for index in range(32))


class FinalEvidenceRunnerError(RuntimeError):
    """Raised when observed final evidence is malformed or inconsistent."""


def run_final_evidence(
    repository_root: Path,
    manifest_path: Path,
    *,
    base_sha: str,
    head_sha: str,
) -> tuple[ClosureReport, ClosureReport, ClosureReport, ClosureReport]:
    root = repository_root.resolve()
    document = _object(json.loads(manifest_path.read_text(encoding="utf-8")), "manifest")
    if document.get("contract_version") != FINAL_EVIDENCE_MANIFEST_VERSION:
        raise FinalEvidenceRunnerError("unsupported final evidence manifest version")
    if document.get("scope") != "SOFTWARE_FACTORY_IMPLEMENTATION":
        raise FinalEvidenceRunnerError("final evidence manifest scope is not Software Factory implementation")
    if document.get("repository") != "Aliturgutt/ilaios":
        raise FinalEvidenceRunnerError("final evidence repository identity mismatch")

    raw_phases = document.get("phases")
    if not isinstance(raw_phases, list):
        raise FinalEvidenceRunnerError("manifest phases must be a list")
    phase_evidence: list[PhaseEvidence] = []
    observed_ok: dict[str, bool] = {}
    lineage_ok = True
    for raw in raw_phases:
        item = _object(raw, "phase evidence")
        phase = _text(item, "phase")
        pr_number = _positive_int(item, "pr_number")
        ci_run_id = _positive_int(item, "ci_run_id")
        ci_workflow = _text(item, "ci_workflow")
        ci_conclusion = _text(item, "ci_conclusion")
        phase_head = _text(item, "head_sha")
        merge_sha = _text(item, "merge_sha")
        merged = _boolean(item, "merged")
        exact_head_ci = _boolean(item, "exact_head_ci_passed")
        evidence_digest = _text(item, "evidence_digest")
        digest_material = {
            "phase": phase,
            "pr_number": pr_number,
            "head_sha": phase_head,
            "merge_sha": merge_sha,
            "ci_run_id": ci_run_id,
            "ci_workflow": ci_workflow,
            "ci_conclusion": ci_conclusion,
            "merged": merged,
            "exact_head_ci_passed": exact_head_ci,
        }
        expected_digest = hashlib.sha256(
            json.dumps(digest_material, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        if evidence_digest != expected_digest:
            raise FinalEvidenceRunnerError(f"phase evidence digest mismatch: {phase}")
        if ci_conclusion != "success":
            raise FinalEvidenceRunnerError(f"phase CI conclusion is not success: {phase}")
        phase_lineage = _phase_integrated(root, phase_head, merge_sha, head_sha)
        lineage_ok = lineage_ok and phase_lineage
        if not phase_lineage:
            raise FinalEvidenceRunnerError(
                f"phase merge integration is not contained or content-equivalent in final head: {phase}"
            )
        ok = merged and exact_head_ci and ci_conclusion == "success"
        observed_ok[phase] = ok
        phase_evidence.append(
            PhaseEvidence(
                phase=phase,
                merged=merged,
                exact_head_ci_passed=exact_head_ci,
                head_sha=phase_head,
                merge_sha=merge_sha,
                evidence_digest=evidence_digest,
            )
        )

    if tuple(sorted(observed_ok, key=_phase_index)) != EXPECTED_PHASES:
        raise FinalEvidenceRunnerError("phase manifest must contain exactly SF-0 through SF-31")
    all_phases = all(observed_ok.get(phase, False) for phase in EXPECTED_PHASES)

    sf29, sf30, sf31 = run_repository_assurance(root, base_sha=base_sha, head_sha=head_sha)
    if not (sf29.passed and sf30.passed and sf31.passed):
        raise FinalEvidenceRunnerError("SF-29 through SF-31 repository assurance is not passing")

    commercial_package = SoftwareFactoryCommercialPackage().audit(root)
    reconciler = SoftwareFactoryFinalReconciliation()
    commercial = reconciler.commercial_licensing_package(
        CommercialLicensingEvidence(
            dependency_governance_passed=observed_ok["SF-13"],
            license_provenance_passed=observed_ok["SF-14"],
            sbom_bound=observed_ok["SF-15"],
            imported_code_text_resolved=commercial_package.imported_code_text_resolved,
            commercial_compatibility_resolved=commercial_package.commercial_compatibility_resolved,
            restrictive_or_unknown_license_present=commercial_package.restrictive_or_unknown_license_present,
            ai_ip_clearance_claimed=commercial_package.ai_ip_clearance_claimed,
            package_manifest_present=commercial_package.package_manifest_present,
        ),
        base_sha=base_sha,
        head_sha=head_sha,
    )

    e2e = reconciler.e2e_acceptance(
        E2EAcceptanceEvidence(
            repository_analysis_passed=observed_ok["SF-5"],
            governed_changeset_passed=all(observed_ok[f"SF-{index}"] for index in range(5)),
            validation_passed=observed_ok["SF-11"],
            independent_review_passed=observed_ok["SF-12"],
            security_review_passed=observed_ok["SF-12"],
            dependency_license_passed=observed_ok["SF-13"] and observed_ok["SF-14"],
            sbom_build_signing_bound=all(observed_ok[f"SF-{index}"] for index in range(15, 18)),
            db_api_safety_passed=observed_ok["SF-20"] and observed_ok["SF-21"],
            retry_cost_observability_passed=all(observed_ok[f"SF-{index}"] for index in range(22, 25)),
            promotion_gateway_passed=observed_ok["SF-25"],
            pr_ci_path_passed=observed_ok["SF-26"],
            recovery_passed=observed_ok["SF-28"],
            skill_redteam_docs_passed=all(observed_ok[f"SF-{index}"] for index in range(29, 32)),
            direct_production_mutation_observed=False,
        ),
        base_sha=base_sha,
        head_sha=head_sha,
    )

    architecture_files = (
        "docs/canonical/SYSTEM_ARCHITECTURE.md",
        "docs/canonical/AUTONOMOUS_NODE_ARCHITECTURE.md",
        "docs/canonical/DEPENDENCY_GRAPH.md",
        "docs/governance/GOVERNANCE.md",
    )
    architecture_present = all((root / path).is_file() for path in architecture_files)
    first_pass = CompletenessPassEvidence(
        pass_name="architecture-capability-dependency-phase",
        architecture_complete=architecture_present,
        capability_complete=all_phases,
        dependency_complete=all(observed_ok[f"SF-{index}"] for index in range(13, 18)),
        phase_complete=all_phases,
        code_test_ci_consistent=all_phases,
        documentation_consistent=sf31.passed,
        evidence_consistent=lineage_ok,
    )
    second_pass = CompletenessPassEvidence(
        pass_name="code-test-ci-document-evidence",
        architecture_complete=sf31.passed,
        capability_complete=sf29.passed and sf30.passed,
        dependency_complete=commercial_package.passed,
        phase_complete=len(phase_evidence) == 32,
        code_test_ci_consistent=all(item.exact_head_ci_passed for item in phase_evidence),
        documentation_consistent=sf31.passed,
        evidence_consistent=lineage_ok and all(len(item.evidence_digest) == 64 for item in phase_evidence),
    )
    completeness = reconciler.two_pass_completeness(
        first_pass,
        second_pass,
        base_sha=base_sha,
        head_sha=head_sha,
    )

    external_blockers_raw = document.get("external_blockers", [])
    if not isinstance(external_blockers_raw, list) or not all(isinstance(item, str) for item in external_blockers_raw):
        raise FinalEvidenceRunnerError("external_blockers must be a string list")
    final = reconciler.final_evidence_reconciliation(
        FinalEvidence(
            phases=tuple(phase_evidence),
            commercial_licensing_passed=commercial.disposition is ClosureDisposition.PASS,
            e2e_acceptance_passed=e2e.disposition is ClosureDisposition.PASS,
            two_pass_completeness_passed=completeness.disposition is ClosureDisposition.PASS,
            external_blockers=tuple(cast(list[str], external_blockers_raw)),
            deployment_evidence_present=False,
        ),
        base_sha=base_sha,
        head_sha=head_sha,
    )
    return commercial, e2e, completeness, final


def _phase_integrated(root: Path, phase_head: str, merge_sha: str, final_head: str) -> bool:
    """Verify a historical phase across both merge-commit and squash-merge histories.

    A normal merge must retain the tested PR head in Git ancestry. Older phases were
    squash-merged by GitHub, so their tested head cannot be an ancestor of the
    resulting single-parent commit. For that bounded historical case, require the
    squash commit to introduce exactly the same changed-path set and exact final
    blobs as the tested PR head, then require the resulting merge/squash commit to
    remain in the final head ancestry.
    """

    if not _is_ancestor(root, merge_sha, final_head):
        return False
    if _is_ancestor(root, phase_head, merge_sha):
        return True
    return _squash_content_equivalent(root, phase_head, merge_sha)


def _squash_content_equivalent(root: Path, phase_head: str, merge_sha: str) -> bool:
    parents = _commit_parents(root, merge_sha)
    if len(parents) != 1:
        return False
    merge_parent = parents[0]
    merge_base = _git_text(root, "merge-base", phase_head, merge_parent)
    if not merge_base:
        return False
    phase_paths = _changed_paths(root, merge_base, phase_head)
    merge_paths = _changed_paths(root, merge_parent, merge_sha)
    if not phase_paths or phase_paths != merge_paths:
        return False
    return all(_blob_sha(root, phase_head, path) == _blob_sha(root, merge_sha, path) for path in phase_paths)


def _commit_parents(root: Path, sha: str) -> tuple[str, ...]:
    line = _git_text(root, "rev-list", "--parents", "-n", "1", sha)
    fields = line.split()
    if not fields or fields[0] != sha:
        return ()
    return tuple(fields[1:])


def _changed_paths(root: Path, base: str, head: str) -> tuple[str, ...]:
    output = _git_text(root, "diff", "--name-only", "--no-renames", base, head)
    return tuple(sorted(path for path in output.splitlines() if path))


def _blob_sha(root: Path, commit: str, path: str) -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", f"{commit}:{path}"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def _git_text(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=root,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return completed.returncode == 0


def _phase_index(phase: str) -> int:
    try:
        return int(phase.removeprefix("SF-"))
    except ValueError as error:
        raise FinalEvidenceRunnerError(f"invalid phase identity: {phase}") from error


def _object(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise FinalEvidenceRunnerError(f"{label} must be an object")
    return cast(dict[str, object], value)


def _text(document: Mapping[str, object], key: str) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value.strip():
        raise FinalEvidenceRunnerError(f"{key} must be a non-empty string")
    return value


def _positive_int(document: Mapping[str, object], key: str) -> int:
    value = document.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise FinalEvidenceRunnerError(f"{key} must be a positive integer")
    return value


def _boolean(document: Mapping[str, object], key: str) -> bool:
    value = document.get(key)
    if not isinstance(value, bool):
        raise FinalEvidenceRunnerError(f"{key} must be boolean")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--head-sha", required=True)
    arguments = parser.parse_args(argv)
    try:
        reports = run_final_evidence(
            arguments.repository_root,
            arguments.manifest,
            base_sha=arguments.base_sha,
            head_sha=arguments.head_sha,
        )
    except (OSError, json.JSONDecodeError, FinalEvidenceRunnerError) as error:
        print(f"Software Factory final evidence failed closed: {error}")
        return 2
    for report in reports:
        print(f"{report.stage}: {report.disposition.value} {report.report_sha256}")
        for finding in report.findings:
            print(f"{finding.disposition.value} {finding.finding_id} {finding.subject}: {finding.reason}")
    final = reports[-1]
    return 0 if final.passed and final.final_completion_claimed else 1


if __name__ == "__main__":
    raise SystemExit(main())

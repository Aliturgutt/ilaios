from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from services.software_factory_api_contract_safety import (
    APIContractSafetyError,
    ContractChange,
    ContractDisposition,
    SoftwareFactoryAPIContractSafety,
    audit_repository_change,
)

BASE = "1" * 40
HEAD = "2" * 40


def test_additive_contract_change_passes() -> None:
    report = SoftwareFactoryAPIContractSafety().evaluate(
        (
            ContractChange(
                contract_id="jobs-v1-additive",
                surface="POST /v1/jobs",
                public=True,
            ),
        ),
        base_sha=BASE,
        head_sha=HEAD,
    )

    assert report.disposition is ContractDisposition.PASS
    assert report.passed is True
    assert report.acceptance_authorized is False
    assert report.promotion_authorized is False
    assert report.deployment_authorized is False
    assert report.production_mutation_authorized is False


def test_silent_breaking_change_is_blocked() -> None:
    report = SoftwareFactoryAPIContractSafety().evaluate(
        (
            ContractChange(
                contract_id="jobs-remove-field",
                surface="Job.status",
                public=True,
                field_removed=True,
                affected_consumers_identified=True,
                migration_notes_present=True,
                independent_review_present=True,
            ),
        ),
        base_sha=BASE,
        head_sha=HEAD,
    )

    assert report.disposition is ContractDisposition.BLOCK
    assert {item.finding_id for item in report.findings} == {"SF21-SILENT-BREAK"}


def test_versioned_break_without_migration_evidence_is_blocked() -> None:
    report = SoftwareFactoryAPIContractSafety().evaluate(
        (
            ContractChange(
                contract_id="jobs-v2",
                surface="Job.state",
                public=True,
                type_narrowed=True,
                versioned_break=True,
                independent_review_present=True,
            ),
        ),
        base_sha=BASE,
        head_sha=HEAD,
    )

    assert report.disposition is ContractDisposition.BLOCK
    assert any(
        item.finding_id == "SF21-MISSING-MIGRATION-EVIDENCE"
        for item in report.findings
    )


def test_breaking_change_requires_independent_review() -> None:
    report = SoftwareFactoryAPIContractSafety().evaluate(
        (
            ContractChange(
                contract_id="jobs-v2",
                surface="DELETE /v1/jobs/{id}",
                endpoint_removed=True,
                versioned_break=True,
                affected_consumers_identified=True,
                migration_notes_present=True,
            ),
        ),
        base_sha=BASE,
        head_sha=HEAD,
    )

    assert report.disposition is ContractDisposition.REVIEW_REQUIRED
    assert report.independent_review_required is True
    assert any(
        item.finding_id == "SF21-INDEPENDENT-REVIEW"
        for item in report.findings
    )


def test_auth_and_idempotency_changes_require_review() -> None:
    report = SoftwareFactoryAPIContractSafety().evaluate(
        (
            ContractChange(
                contract_id="approval-auth",
                surface="POST /v1/approvals",
                public=True,
                auth_semantics_changed=True,
                idempotency_semantics_changed=True,
                independent_review_present=True,
            ),
        ),
        base_sha=BASE,
        head_sha=HEAD,
    )

    assert report.disposition is ContractDisposition.REVIEW_REQUIRED
    identifiers = {item.finding_id for item in report.findings}
    assert "SF21-PUBLIC-AUTH-SEMANTICS" in identifiers
    assert "SF21-IDEMPOTENCY-SEMANTICS" in identifiers


def test_malformed_change_fails_closed() -> None:
    with pytest.raises(APIContractSafetyError, match="unknown API contract"):
        ContractChange.from_mapping(
            {
                "contract_id": "jobs",
                "surface": "GET /v1/jobs",
                "ignore_policy": True,
            }
        )

    with pytest.raises(APIContractSafetyError, match="must be boolean"):
        ContractChange.from_mapping(
            {
                "contract_id": "jobs",
                "surface": "GET /v1/jobs",
                "field_removed": "yes",
            }
        )


def test_invalid_lineage_sha_fails_closed() -> None:
    with pytest.raises(APIContractSafetyError, match="40-character SHA"):
        SoftwareFactoryAPIContractSafety().evaluate(
            (), base_sha="master", head_sha=HEAD
        )


def test_report_is_deterministic() -> None:
    changes = (
        ContractChange(
            contract_id="jobs",
            surface="POST /v1/jobs",
            behavior_semantics_changed=True,
            independent_review_present=True,
        ),
    )
    gate = SoftwareFactoryAPIContractSafety()
    first = gate.evaluate(changes, base_sha=BASE, head_sha=HEAD)
    second = gate.evaluate(changes, base_sha=BASE, head_sha=HEAD)
    assert first.report_sha256 == second.report_sha256


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ("git", *args),
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _init_repository(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-b", "master")
    _git(root, "config", "user.email", "test@ilaios.invalid")
    _git(root, "config", "user.name", "ILAIOS Test")
    (root / "README.md").write_text("baseline\n", encoding="utf-8")
    _git(root, "add", "README.md")
    _git(root, "commit", "-m", "baseline")
    return root, _git(root, "rev-parse", "HEAD")


def test_non_contract_changeset_needs_no_contract_evidence(tmp_path: Path) -> None:
    root, base = _init_repository(tmp_path)
    (root / "README.md").write_text("baseline\nmore\n", encoding="utf-8")
    _git(root, "add", "README.md")
    _git(root, "commit", "-m", "docs")
    head = _git(root, "rev-parse", "HEAD")

    report = audit_repository_change(root, base_sha=base, head_sha=head)
    assert report.disposition is ContractDisposition.PASS
    assert report.changes_evaluated == 0


def test_machine_contract_change_without_evidence_is_blocked(tmp_path: Path) -> None:
    root, base = _init_repository(tmp_path)
    contract = root / "contracts" / "openapi.yaml"
    contract.parent.mkdir()
    contract.write_text("openapi: 3.0.0\n", encoding="utf-8")
    _git(root, "add", str(contract.relative_to(root)))
    _git(root, "commit", "-m", "contract")
    head = _git(root, "rev-parse", "HEAD")

    report = audit_repository_change(root, base_sha=base, head_sha=head)
    assert report.disposition is ContractDisposition.BLOCK


def test_machine_contract_change_uses_structured_evidence(tmp_path: Path) -> None:
    root, base = _init_repository(tmp_path)
    contract = root / "contracts" / "openapi.yaml"
    contract.parent.mkdir()
    contract.write_text("openapi: 3.0.0\n", encoding="utf-8")
    evidence = root / "evidence" / "software_factory" / "api_contract_safety.json"
    evidence.parent.mkdir(parents=True)
    evidence.write_text(
        json.dumps(
            {
                "changes": [
                    {
                        "contract_id": "openapi-additive",
                        "surface": "GET /v1/health",
                        "public": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    _git(root, "add", ".")
    _git(root, "commit", "-m", "contract")
    head = _git(root, "rev-parse", "HEAD")

    report = audit_repository_change(root, base_sha=base, head_sha=head)
    assert report.disposition is ContractDisposition.PASS


def test_evidence_cannot_request_policy_bypass() -> None:
    with pytest.raises(APIContractSafetyError, match="unknown API contract"):
        ContractChange.from_mapping(
            {
                "contract_id": "malicious",
                "surface": "POST /v1/jobs",
                "mark_compatible_without_review": True,
            }
        )

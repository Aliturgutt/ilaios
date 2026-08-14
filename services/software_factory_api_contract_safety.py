"""SF-21 fail-closed API contract safety for the Software Factory.

This module is a read-only compatibility/admission gate. It does not define a
second API authority, execute deployments, mutate production, or self-approve
breaking changes. Canonical API truth remains docs/canonical/API_CONTRACTS.md
and the existing sf-api-contract skill remains the planning surface.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Mapping, Sequence

API_CONTRACT_SAFETY_VERSION = "1.0.0"
_SHA = re.compile(r"^[0-9a-f]{40}$")


class APIContractSafetyError(RuntimeError):
    """Raised when SF-21 cannot establish a trustworthy contract decision."""


class ContractDisposition(str, Enum):
    PASS = "PASS"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class ContractChange:
    """Normalized API-contract change emitted by the canonical planning skill."""

    contract_id: str
    surface: str
    public: bool = False
    field_removed: bool = False
    required_field_added: bool = False
    type_narrowed: bool = False
    enum_value_removed: bool = False
    response_status_removed: bool = False
    endpoint_removed: bool = False
    auth_semantics_changed: bool = False
    idempotency_semantics_changed: bool = False
    behavior_semantics_changed: bool = False
    versioned_break: bool = False
    affected_consumers_identified: bool = False
    migration_notes_present: bool = False
    independent_review_present: bool = False

    @property
    def breaking(self) -> bool:
        return any(
            (
                self.field_removed,
                self.required_field_added,
                self.type_narrowed,
                self.enum_value_removed,
                self.response_status_removed,
                self.endpoint_removed,
            )
        )

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> ContractChange:
        allowed = {field.name for field in cls.__dataclass_fields__.values()}
        unknown = set(raw) - allowed
        if unknown:
            raise APIContractSafetyError(
                "unknown API contract change fields: " + ", ".join(sorted(unknown))
            )
        contract_id = raw.get("contract_id")
        surface = raw.get("surface")
        if not isinstance(contract_id, str) or not contract_id.strip():
            raise APIContractSafetyError("contract_id must be a non-blank string")
        if not isinstance(surface, str) or not surface.strip():
            raise APIContractSafetyError("surface must be a non-blank string")
        values: dict[str, object] = {
            "contract_id": contract_id.strip(),
            "surface": surface.strip(),
        }
        for name in allowed - {"contract_id", "surface"}:
            value = raw.get(name, False)
            if not isinstance(value, bool):
                raise APIContractSafetyError(f"{name} must be boolean")
            values[name] = value
        return cls(**values)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class ContractFinding:
    finding_id: str
    disposition: ContractDisposition
    contract_id: str
    reason: str
    remediation: str


@dataclass(frozen=True, slots=True)
class APIContractSafetyReport:
    contract_version: str
    base_sha: str
    head_sha: str
    scope: str
    changes_evaluated: int
    findings: tuple[ContractFinding, ...]
    disposition: ContractDisposition
    passed: bool
    independent_review_required: bool
    acceptance_authorized: bool
    promotion_authorized: bool
    deployment_authorized: bool
    production_mutation_authorized: bool
    report_sha256: str


class SoftwareFactoryAPIContractSafety:
    """Deterministic SF-21 compatibility gate."""

    def evaluate(
        self,
        changes: Sequence[ContractChange],
        *,
        base_sha: str,
        head_sha: str,
        scope: str = "REVIEWED_CHANGESET",
    ) -> APIContractSafetyReport:
        _require_sha(base_sha, "base_sha")
        _require_sha(head_sha, "head_sha")
        if not scope.strip():
            raise APIContractSafetyError("scope is required")

        findings: list[ContractFinding] = []
        seen: set[str] = set()
        for change in changes:
            if change.contract_id in seen:
                raise APIContractSafetyError(
                    f"duplicate contract_id: {change.contract_id}"
                )
            seen.add(change.contract_id)
            findings.extend(self._evaluate_change(change))

        normalized = tuple(
            sorted(
                findings,
                key=lambda item: (
                    item.disposition.value,
                    item.contract_id,
                    item.finding_id,
                ),
            )
        )
        disposition = _overall_disposition(normalized)
        review_required = any(
            item.disposition is ContractDisposition.REVIEW_REQUIRED
            for item in normalized
        )
        material = {
            "contract_version": API_CONTRACT_SAFETY_VERSION,
            "base_sha": base_sha,
            "head_sha": head_sha,
            "scope": scope,
            "changes": [asdict(change) for change in changes],
            "findings": [
                {
                    **asdict(item),
                    "disposition": item.disposition.value,
                }
                for item in normalized
            ],
            "disposition": disposition.value,
            "authority": {
                "acceptance": False,
                "promotion": False,
                "deployment": False,
                "production_mutation": False,
            },
        }
        return APIContractSafetyReport(
            contract_version=API_CONTRACT_SAFETY_VERSION,
            base_sha=base_sha,
            head_sha=head_sha,
            scope=scope,
            changes_evaluated=len(changes),
            findings=normalized,
            disposition=disposition,
            passed=disposition is ContractDisposition.PASS,
            independent_review_required=review_required,
            acceptance_authorized=False,
            promotion_authorized=False,
            deployment_authorized=False,
            production_mutation_authorized=False,
            report_sha256=_sha256_json(material),
        )

    @staticmethod
    def _evaluate_change(change: ContractChange) -> tuple[ContractFinding, ...]:
        findings: list[ContractFinding] = []
        if change.breaking and not change.versioned_break:
            findings.append(
                ContractFinding(
                    "SF21-SILENT-BREAK",
                    ContractDisposition.BLOCK,
                    change.contract_id,
                    "breaking API change has no explicit version boundary",
                    "version the breaking surface or redesign it as a compatible additive change",
                )
            )

        if change.breaking and (
            not change.affected_consumers_identified
            or not change.migration_notes_present
        ):
            findings.append(
                ContractFinding(
                    "SF21-MISSING-MIGRATION-EVIDENCE",
                    ContractDisposition.BLOCK,
                    change.contract_id,
                    "breaking change lacks affected-consumer or migration evidence",
                    "identify affected consumers and attach migration/compatibility notes",
                )
            )

        sensitive_semantics = any(
            (
                change.auth_semantics_changed,
                change.idempotency_semantics_changed,
                change.behavior_semantics_changed,
            )
        )
        if change.breaking or sensitive_semantics:
            if not change.independent_review_present:
                findings.append(
                    ContractFinding(
                        "SF21-INDEPENDENT-REVIEW",
                        ContractDisposition.REVIEW_REQUIRED,
                        change.contract_id,
                        "contract compatibility or security semantics require independent review",
                        "obtain review independent from the implementation skill path",
                    )
                )

        if change.public and change.auth_semantics_changed:
            findings.append(
                ContractFinding(
                    "SF21-PUBLIC-AUTH-SEMANTICS",
                    ContractDisposition.REVIEW_REQUIRED,
                    change.contract_id,
                    "public authentication/authorization semantics changed",
                    "review least-privilege, client compatibility, and migration behavior",
                )
            )
        if change.idempotency_semantics_changed:
            findings.append(
                ContractFinding(
                    "SF21-IDEMPOTENCY-SEMANTICS",
                    ContractDisposition.REVIEW_REQUIRED,
                    change.contract_id,
                    "idempotency semantics changed and can alter duplicate-side-effect safety",
                    "prove replay safety and mixed-version client behavior",
                )
            )
        return tuple(findings)


def audit_repository_change(
    repository_root: Path,
    *,
    base_sha: str,
    head_sha: str,
) -> APIContractSafetyReport:
    """Audit exact reviewed changeset and require structured evidence for contracts.

    Machine-readable API artifacts are detected from changed paths. When such a
    contract changes, SF-21 requires an evidence JSON file at
    `evidence/software_factory/api_contract_safety.json`. The evidence is then
    evaluated by the same deterministic policy. No evidence is required for a
    changeset that does not modify machine-readable contract artifacts.
    """

    _require_sha(base_sha, "base_sha")
    _require_sha(head_sha, "head_sha")
    changed = _git_lines(
        repository_root,
        "diff",
        "--name-only",
        base_sha,
        head_sha,
        "--",
    )
    contract_paths = tuple(
        path for path in changed if path and _is_machine_contract_path(path)
    )
    gate = SoftwareFactoryAPIContractSafety()
    if not contract_paths:
        return gate.evaluate((), base_sha=base_sha, head_sha=head_sha)

    evidence_path = (
        repository_root / "evidence/software_factory/api_contract_safety.json"
    )
    if not evidence_path.is_file():
        synthetic = ContractChange(
            contract_id="changeset-contract-evidence",
            surface=",".join(contract_paths),
            field_removed=True,
        )
        return gate.evaluate((synthetic,), base_sha=base_sha, head_sha=head_sha)

    try:
        raw = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise APIContractSafetyError("API contract evidence is unreadable") from error
    if not isinstance(raw, dict) or not isinstance(raw.get("changes"), list):
        raise APIContractSafetyError("API contract evidence must contain a changes list")
    changes = tuple(
        ContractChange.from_mapping(item)
        for item in raw["changes"]
        if isinstance(item, dict)
    )
    if len(changes) != len(raw["changes"]):
        raise APIContractSafetyError("API contract evidence changes must be objects")
    if not changes:
        raise APIContractSafetyError("changed API contracts require non-empty evidence")
    return gate.evaluate(changes, base_sha=base_sha, head_sha=head_sha)


def _is_machine_contract_path(path: str) -> bool:
    normalized = path.replace("\\", "/").casefold()
    name = normalized.rsplit("/", 1)[-1]
    suffix = Path(name).suffix
    if suffix == ".proto":
        return True
    if suffix not in {".json", ".yaml", ".yml"}:
        return False
    return any(
        marker in normalized
        for marker in (
            "/openapi",
            "/swagger",
            "/contracts/",
            "/api/schema",
            "/api/contracts",
        )
    ) or name.startswith(("openapi.", "swagger."))


def _overall_disposition(
    findings: Sequence[ContractFinding],
) -> ContractDisposition:
    if any(item.disposition is ContractDisposition.BLOCK for item in findings):
        return ContractDisposition.BLOCK
    if any(
        item.disposition is ContractDisposition.REVIEW_REQUIRED for item in findings
    ):
        return ContractDisposition.REVIEW_REQUIRED
    return ContractDisposition.PASS


def _require_sha(value: str, label: str) -> None:
    if _SHA.fullmatch(value) is None:
        raise APIContractSafetyError(f"{label} must be a lowercase 40-character SHA")


def _sha256_json(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _git_lines(repository_root: Path, *arguments: str) -> tuple[str, ...]:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=repository_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise APIContractSafetyError(
            "git contract-scope discovery failed closed: " + completed.stderr.strip()
        )
    return tuple(line.strip() for line in completed.stdout.splitlines())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--head-sha", required=True)
    arguments = parser.parse_args(argv)
    try:
        report = audit_repository_change(
            arguments.repository_root,
            base_sha=arguments.base_sha,
            head_sha=arguments.head_sha,
        )
    except APIContractSafetyError as error:
        print(f"SF-21 API contract safety failed closed: {error}")
        return 2
    print(f"SF-21 API contract safety report: {report.report_sha256}")
    print(f"SF-21 disposition: {report.disposition.value}")
    for finding in report.findings:
        print(
            f"{finding.disposition.value} {finding.finding_id} "
            f"{finding.contract_id}: {finding.reason}"
        )
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

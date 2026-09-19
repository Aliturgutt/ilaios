"""Software Factory commercial-package engineering audit.

This audit is deliberately scoped to the first-party Software Factory implementation.
It does not clear the whole ILAIOS product for commercial distribution and does not
provide legal advice or an IP warranty. Repository-wide website/desktop/release
license inventories remain separate release gates.
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from services.software_factory import SoftwareFactoryError
from services.software_factory_skills import SkillRegistry, default_skills_root

COMMERCIAL_PACKAGE_VERSION = "1.0.0"
_SCOPE = "SOFTWARE_FACTORY_IMPLEMENTATION"
_INTERNAL_IMPORTS = frozenset({"services", "src", "packages"})
_APPROVED_EXTERNALS: dict[str, tuple[str, str, str]] = {
    "yaml": ("PyYAML", "MIT", "PyPI package metadata"),
    "requests": ("requests", "Apache-2.0", "PyPI package metadata"),
    "dotenv": ("python-dotenv", "BSD-3-Clause", "PyPI package metadata"),
}


@dataclass(frozen=True, slots=True)
class PackageFinding:
    finding_id: str
    subject: str
    reason: str
    remediation: str


@dataclass(frozen=True, slots=True)
class PackageFile:
    path: str
    sha256: str


@dataclass(frozen=True, slots=True)
class ExternalDependency:
    module: str
    distribution: str
    license_id: str
    evidence_source: str


@dataclass(frozen=True, slots=True)
class CommercialPackageReport:
    contract_version: str
    scope: str
    files: tuple[PackageFile, ...]
    external_dependencies: tuple[ExternalDependency, ...]
    canonical_skill_count: int
    findings: tuple[PackageFinding, ...]
    imported_code_text_resolved: bool
    commercial_compatibility_resolved: bool
    restrictive_or_unknown_license_present: bool
    package_manifest_present: bool
    ai_ip_clearance_claimed: bool
    passed: bool
    deployment_authorized: bool
    production_mutation_authorized: bool
    report_sha256: str


class SoftwareFactoryCommercialPackage:
    """Build and audit a content-addressed first-party Software Factory package."""

    def audit(self, repository_root: Path) -> CommercialPackageReport:
        root = repository_root.resolve()
        findings: list[PackageFinding] = []

        license_decision = root / "docs/governance/LICENSE_DECISION.md"
        if not license_decision.is_file():
            findings.append(_finding("COMM-LICENSE-DECISION", str(license_decision), "license decision is missing", "restore the controlled repository license decision"))
        else:
            text = license_decision.read_text(encoding="utf-8")
            if "PRIVATE / PROPRIETARY BY DEFAULT" not in text or "Third-party dependencies remain subject to their own licenses" not in text:
                findings.append(_finding("COMM-LICENSE-POSTURE", "docs/governance/LICENSE_DECISION.md", "controlled proprietary posture or third-party dependency boundary is missing", "restore the controlled licensing posture without inventing an open-source grant"))

        provenance_audit = root / "docs/governance/IP_LICENSE_PROVENANCE_AUDIT.md"
        if not provenance_audit.is_file():
            findings.append(_finding("COMM-PROVENANCE-AUDIT", str(provenance_audit), "IP/license provenance audit is missing", "restore the engineering provenance audit"))
        elif "This document is engineering evidence, not legal advice." not in provenance_audit.read_text(encoding="utf-8"):
            findings.append(_finding("COMM-LEGAL-BOUNDARY", "docs/governance/IP_LICENSE_PROVENANCE_AUDIT.md", "engineering-vs-legal truth boundary is missing", "restore the no-legal-warranty boundary"))

        registry: SkillRegistry | None = None
        try:
            registry = SkillRegistry(default_skills_root(root))
        except SoftwareFactoryError as error:
            findings.append(_finding("COMM-SKILL-PROVENANCE", "tools/software-factory/skills", f"canonical skill provenance failed closed: {error}", "repair the first-party skill package provenance; do not bypass the registry"))

        python_files = tuple(sorted((root / "services").glob("software_factory*.py")))
        if not python_files:
            findings.append(_finding("COMM-SERVICE-SCOPE", "services/software_factory*.py", "Software Factory service scope is empty", "restore the canonical Software Factory service implementation"))

        external_modules: set[str] = set()
        for path in python_files:
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (OSError, SyntaxError) as error:
                findings.append(_finding("COMM-SOURCE-PARSE", _relative(root, path), f"source cannot be deterministically parsed: {error}", "repair the source before commercial packaging"))
                continue
            for node in ast.walk(tree):
                names: list[str] = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                for name in names:
                    top = name.split(".", 1)[0]
                    if top in sys.stdlib_module_names or top in _INTERNAL_IMPORTS:
                        continue
                    external_modules.add(top)

        dependencies: list[ExternalDependency] = []
        for module in sorted(external_modules):
            evidence = _APPROVED_EXTERNALS.get(module)
            if evidence is None:
                findings.append(_finding("COMM-UNKNOWN-DEPENDENCY", module, "Software Factory imports a dependency without reviewed commercial-license evidence", "classify the dependency, record license/provenance evidence, and rerun the package audit"))
                continue
            distribution, license_id, source = evidence
            dependencies.append(ExternalDependency(module, distribution, license_id, source))

        files = _package_files(root)
        if not files:
            findings.append(_finding("COMM-MANIFEST", _SCOPE, "content-addressed package manifest is empty", "restore Software Factory package files before closure"))

        normalized = tuple(sorted(findings, key=lambda item: (item.subject, item.finding_id, item.reason)))
        restrictive_or_unknown = any(item.finding_id == "COMM-UNKNOWN-DEPENDENCY" for item in normalized)
        imported_resolved = registry is not None
        compatibility_resolved = imported_resolved and not restrictive_or_unknown and not normalized
        material = {
            "contract_version": COMMERCIAL_PACKAGE_VERSION,
            "scope": _SCOPE,
            "files": [{"path": item.path, "sha256": item.sha256} for item in files],
            "external_dependencies": [
                {"module": item.module, "distribution": item.distribution, "license_id": item.license_id, "evidence_source": item.evidence_source}
                for item in dependencies
            ],
            "canonical_skill_count": 0 if registry is None else len(registry.skill_ids),
            "findings": [
                {"finding_id": item.finding_id, "subject": item.subject, "reason": item.reason, "remediation": item.remediation}
                for item in normalized
            ],
            "truth_boundary": {
                "whole_product_release_clearance": False,
                "legal_advice": False,
                "ip_warranty": False,
                "deployment_authority": False,
                "production_mutation_authority": False,
            },
        }
        digest = hashlib.sha256(json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        return CommercialPackageReport(
            contract_version=COMMERCIAL_PACKAGE_VERSION,
            scope=_SCOPE,
            files=files,
            external_dependencies=tuple(dependencies),
            canonical_skill_count=0 if registry is None else len(registry.skill_ids),
            findings=normalized,
            imported_code_text_resolved=imported_resolved,
            commercial_compatibility_resolved=compatibility_resolved,
            restrictive_or_unknown_license_present=restrictive_or_unknown,
            package_manifest_present=bool(files),
            ai_ip_clearance_claimed=False,
            passed=not normalized,
            deployment_authorized=False,
            production_mutation_authorized=False,
            report_sha256=digest,
        )


def _package_files(root: Path) -> tuple[PackageFile, ...]:
    candidates: set[Path] = set((root / "services").glob("software_factory*.py"))
    skills_root = root / "tools/software-factory/skills"
    if skills_root.is_dir():
        candidates.update(path for path in skills_root.rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    for relative in (
        "docs/governance/SF19_SECRET_SCANNING.md",
        "docs/governance/SF20_DB_MIGRATION_SAFETY.md",
        "docs/governance/SF21_API_CONTRACT_SAFETY.md",
        "docs/governance/SF22_SF28_OPERATIONAL_SAFETY.md",
        "docs/governance/SF29_SF31_ASSURANCE.md",
    ):
        path = root / relative
        if path.is_file():
            candidates.add(path)
    return tuple(
        PackageFile(_relative(root, path), hashlib.sha256(path.read_bytes()).hexdigest())
        for path in sorted(candidates)
    )


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root).as_posix()


def _finding(finding_id: str, subject: str, reason: str, remediation: str) -> PackageFinding:
    return PackageFinding(finding_id, subject, reason, remediation)


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    arguments = parser.parse_args(argv)
    report = SoftwareFactoryCommercialPackage().audit(arguments.repository_root)
    print(f"Commercial Licensing Package [{report.scope}]: {'PASS' if report.passed else 'BLOCK'} {report.report_sha256}")
    for finding in report.findings:
        print(f"BLOCK {finding.finding_id} {finding.subject}: {finding.reason}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

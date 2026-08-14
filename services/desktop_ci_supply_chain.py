"""Fail-closed supply-chain policy for ILAIOS Desktop validation/release workflows."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

DESKTOP_WORKFLOWS = (
    ".github/workflows/desktop-ci.yml",
    ".github/workflows/desktop-windows-release.yml",
    ".github/workflows/desktop-msix-packaging.yml",
    ".github/workflows/desktop-msix-signed-release.yml",
)
_SIGNED = ".github/workflows/desktop-msix-signed-release.yml"
_SHA = re.compile(r"^[0-9a-f]{40}$")
_USES = re.compile(r"^\s*-?\s*uses:\s*([^#\s]+)")
_ALLOWED_SIGNING_SECRETS = {
    "ILAIOS_WINDOWS_SIGNING_PFX_BASE64",
    "ILAIOS_WINDOWS_SIGNING_PFX_PASSWORD",
}
_SECRET = re.compile(r"secrets\.([A-Za-z0-9_]+)")


@dataclass(frozen=True, slots=True)
class DesktopCIFinding:
    finding_id: str
    path: str
    reason: str


@dataclass(frozen=True, slots=True)
class DesktopCIReport:
    findings: tuple[DesktopCIFinding, ...]

    @property
    def passed(self) -> bool:
        return not self.findings


class DesktopCISupplyChainPolicy:
    """Audit Desktop workflow bootstrap and signing boundaries without mutation."""

    def audit(self, repository_root: Path) -> DesktopCIReport:
        root = repository_root.resolve()
        findings: list[DesktopCIFinding] = []
        for relative in DESKTOP_WORKFLOWS:
            path = root / relative
            if not path.is_file():
                findings.append(
                    DesktopCIFinding(
                        "DESKTOP-CI-MISSING",
                        relative,
                        "required Desktop workflow is missing",
                    )
                )
                continue
            text = path.read_text(encoding="utf-8")
            findings.extend(self._audit_workflow(relative, text))
        return DesktopCIReport(
            tuple(sorted(findings, key=lambda item: (item.path, item.finding_id)))
        )

    def _audit_workflow(self, relative: str, text: str) -> list[DesktopCIFinding]:
        findings: list[DesktopCIFinding] = []
        if "pull_request_target:" in text:
            findings.append(
                DesktopCIFinding(
                    "DESKTOP-CI-PR-TARGET",
                    relative,
                    "Desktop workflows must not use pull_request_target",
                )
            )
        if "permissions:\n  contents: read" not in text:
            findings.append(
                DesktopCIFinding(
                    "DESKTOP-CI-PERMISSIONS",
                    relative,
                    "Desktop workflow must declare top-level contents: read",
                )
            )
        for line in text.splitlines():
            match = _USES.match(line)
            if match is None:
                continue
            reference = match.group(1)
            if reference.startswith("./"):
                continue
            _, separator, revision = reference.partition("@")
            if not separator or _SHA.fullmatch(revision) is None:
                findings.append(
                    DesktopCIFinding(
                        "DESKTOP-CI-MUTABLE-ACTION",
                        relative,
                        f"external action must use immutable 40-hex SHA: {reference}",
                    )
                )
        findings.extend(self._audit_checkout(relative, text))
        if "flutter pub get --enforce-lockfile" not in text:
            findings.append(
                DesktopCIFinding(
                    "DESKTOP-CI-FLUTTER-LOCK",
                    relative,
                    "Desktop workflow must resolve Flutter packages from the lockfile",
                )
            )
        secrets = set(_SECRET.findall(text))
        if relative == _SIGNED:
            if "environment: desktop-release-signing" not in text:
                findings.append(
                    DesktopCIFinding(
                        "DESKTOP-CI-SIGNING-ENV",
                        relative,
                        "signed release must use the desktop-release-signing environment",
                    )
                )
            unexpected = secrets - _ALLOWED_SIGNING_SECRETS
            if unexpected:
                findings.append(
                    DesktopCIFinding(
                        "DESKTOP-CI-SIGNING-SECRETS",
                        relative,
                        f"unexpected signing secrets: {sorted(unexpected)}",
                    )
                )
            if not _ALLOWED_SIGNING_SECRETS <= secrets:
                findings.append(
                    DesktopCIFinding(
                        "DESKTOP-CI-SIGNING-INPUTS",
                        relative,
                        "signed release must require both protected signing inputs",
                    )
                )
            if "Remove certificate material" not in text or "if: always()" not in text:
                findings.append(
                    DesktopCIFinding(
                        "DESKTOP-CI-CERT-CLEANUP",
                        relative,
                        "signing certificate material must be removed in an always step",
                    )
                )
        elif secrets:
            findings.append(
                DesktopCIFinding(
                    "DESKTOP-CI-VALIDATION-SECRETS",
                    relative,
                    "non-signing Desktop validation workflows must not consume secrets",
                )
            )
        return findings

    @staticmethod
    def _audit_checkout(relative: str, text: str) -> list[DesktopCIFinding]:
        findings: list[DesktopCIFinding] = []
        lines = text.splitlines()
        for index, line in enumerate(lines):
            if "uses: actions/checkout@" not in line:
                continue
            indent = len(line) - len(line.lstrip())
            block = [line]
            for candidate in lines[index + 1 :]:
                stripped = candidate.strip()
                if not stripped:
                    block.append(candidate)
                    continue
                candidate_indent = len(candidate) - len(candidate.lstrip())
                if candidate_indent < indent and (
                    stripped.startswith("- ") or stripped.endswith(":")
                ):
                    break
                block.append(candidate)
            step = "\n".join(block)
            if "persist-credentials: false" not in step:
                findings.append(
                    DesktopCIFinding(
                        "DESKTOP-CI-CHECKOUT-CREDENTIALS",
                        relative,
                        "checkout must disable persisted repository credentials",
                    )
                )
            if "ref: ${{ github.event.pull_request.head.sha || github.sha }}" not in step and (
                "ref: ${{ github.sha }}" not in step
            ):
                findings.append(
                    DesktopCIFinding(
                        "DESKTOP-CI-CHECKOUT-REF",
                        relative,
                        "checkout must bind to an exact PR head SHA or github.sha",
                    )
                )
        return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Desktop CI supply-chain policy")
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args(argv)
    report = DesktopCISupplyChainPolicy().audit(Path(args.repository_root))
    if report.passed:
        print("ILAIOS Desktop CI supply-chain policy PASS")
        return 0
    for finding in report.findings:
        print(f"BLOCK {finding.finding_id} {finding.path}: {finding.reason}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

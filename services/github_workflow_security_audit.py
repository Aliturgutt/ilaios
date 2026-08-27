"""Repository-wide deterministic GitHub Actions security audit."""

# Final Agent closure exact-master recertification trigger; no audit behavior change.
# Final current-master Web recertification trigger; no audit behavior change.
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

_SHA = re.compile(r"^[0-9a-f]{40}$")
_USES = re.compile(r"^\s*-?\s*uses:\s*([^#\s]+)")
_TOP_PUSH = re.compile(r"(?m)^  push:\s*$")
_TOP_PR = re.compile(r"(?m)^  pull_request:\s*$")
_MANUAL_ONLY = frozenset(
    {
        "aws-r01-canary-apply.yml",
        "aws-r01-image-publish.yml",
        "aws-r01-image-scan.yml",
        "aws-r01-preparation-resources.yml",
        "aws-r02-limited-apply.yml",
        "aws-r03-production-apply.yml",
        "desktop-msix-signed-release.yml",
        "openrouter-production-telemetry-certification.yml",
        "video-provider-production-certification.yml",
    }
)
_SECRET_ALLOWED = frozenset(
    {
        "agent-automated-46-of-47-certification.yml",
        "agent-media-intelligence-live-certification.yml",
        "agent-p0-live-certification.yml",
        "agent-web-live-certification.yml",
        "desktop-msix-signed-release.yml",
        "openrouter-production-telemetry-certification.yml",
        "operations-meta-agent-live-certification.yml",
        "video-native-reference-production-certification.yml",
        "video-provider-production-certification.yml",
        "video-reference-production-certification.yml",
    }
)
_TRUSTED_MASTER_SECRET = frozenset(
    {
        "agent-automated-46-of-47-certification.yml",
        "agent-media-intelligence-live-certification.yml",
        "agent-p0-live-certification.yml",
        "agent-web-live-certification.yml",
        "operations-meta-agent-live-certification.yml",
        "video-native-reference-production-certification.yml",
        "video-reference-production-certification.yml",
    }
)


@dataclass(frozen=True, slots=True)
class WorkflowSecurityFinding:
    path: str
    rule: str
    detail: str


def _checkout_blocks(text: str) -> tuple[str, ...]:
    lines = text.splitlines()
    result: list[str] = []
    for index, line in enumerate(lines):
        if "uses: actions/checkout@" not in line:
            continue
        uses_indent = len(line) - len(line.lstrip())
        step_indent = (
            uses_indent if line.lstrip().startswith("- uses:") else max(0, uses_indent - 2)
        )
        block = [line]
        for candidate in lines[index + 1 :]:
            stripped = candidate.lstrip()
            indent = len(candidate) - len(stripped)
            if indent == step_indent and stripped.startswith("- "):
                break
            block.append(candidate)
        result.append("\n".join(block))
    return tuple(result)


def _indirect_manual_only_target(text: str, current_name: str) -> str | None:
    """Reject proxy workflows that auto-dispatch a manual-only workflow."""
    for target in sorted(_MANUAL_ONLY):
        if target == current_name:
            continue
        indicators = (
            f"gh workflow run {target}",
            f"gh workflow run '{target}'",
            f'gh workflow run "{target}"',
            f"/actions/workflows/{target}/dispatches",
        )
        if any(indicator in text for indicator in indicators):
            return target
    return None


def audit_repository(repository_root: Path) -> tuple[WorkflowSecurityFinding, ...]:
    findings: list[WorkflowSecurityFinding] = []
    for path in sorted((repository_root / ".github" / "workflows").glob("*.yml")):
        if path.name.startswith("_redteam-"):
            continue
        relative = path.relative_to(repository_root).as_posix()
        text = path.read_text(encoding="utf-8")
        if "pull_request_target:" in text:
            findings.append(
                WorkflowSecurityFinding(
                    relative, "NO_PR_TARGET", "pull_request_target is forbidden"
                )
            )
        if "permissions: write-all" in text or re.search(
            r"(?m)^  contents:\s+write\s*$", text
        ):
            findings.append(
                WorkflowSecurityFinding(
                    relative,
                    "NO_REPO_WRITE",
                    "permanent workflows may not grant contents write",
                )
            )
        if not re.search(r"(?m)^  contents:\s+read\s*$", text):
            findings.append(
                WorkflowSecurityFinding(
                    relative, "CONTENTS_READ", "explicit contents: read is required"
                )
            )
        if "secrets." in text and path.name not in _SECRET_ALLOWED:
            findings.append(
                WorkflowSecurityFinding(
                    relative, "SECRET_BOUNDARY", "secrets are forbidden in this workflow"
                )
            )
        if path.name in _TRUSTED_MASTER_SECRET:
            if _TOP_PR.search(text):
                findings.append(
                    WorkflowSecurityFinding(
                        relative,
                        "TRUSTED_SECRET_TRIGGER",
                        "secret-bearing certification cannot run from pull_request code",
                    )
                )
            if not _TOP_PUSH.search(text) or "      - master\n" not in text:
                findings.append(
                    WorkflowSecurityFinding(
                        relative,
                        "TRUSTED_SECRET_TRIGGER",
                        "secret-bearing certification must be scoped to master push",
                    )
                )
            if "environment: Production" not in text:
                findings.append(
                    WorkflowSecurityFinding(
                        relative,
                        "TRUSTED_SECRET_ENVIRONMENT",
                        "secret-bearing certification requires Production environment",
                    )
                )
            if "ref: ${{ github.sha }}" not in text:
                findings.append(
                    WorkflowSecurityFinding(
                        relative,
                        "TRUSTED_SECRET_CHECKOUT",
                        "secret-bearing certification must checkout exact trusted github.sha",
                    )
                )
        for line in text.splitlines():
            match = _USES.match(line)
            if match is None:
                continue
            reference = match.group(1)
            if reference.startswith("./"):
                continue
            _, sep, revision = reference.partition("@")
            if not sep or _SHA.fullmatch(revision) is None:
                findings.append(
                    WorkflowSecurityFinding(relative, "IMMUTABLE_ACTION", reference)
                )
        for block in _checkout_blocks(text):
            if "persist-credentials: false" not in block:
                findings.append(
                    WorkflowSecurityFinding(
                        relative,
                        "CHECKOUT_CREDENTIALS",
                        "checkout credentials must not persist",
                    )
                )
            if "ref:" not in block:
                findings.append(
                    WorkflowSecurityFinding(
                        relative,
                        "EXACT_CHECKOUT",
                        "checkout requires explicit exact ref",
                    )
                )
        if path.name in _MANUAL_ONLY:
            if "workflow_dispatch:" not in text:
                findings.append(
                    WorkflowSecurityFinding(
                        relative, "MANUAL_ONLY", "workflow_dispatch is required"
                    )
                )
            if _TOP_PUSH.search(text) or _TOP_PR.search(text):
                findings.append(
                    WorkflowSecurityFinding(
                        relative,
                        "MANUAL_ONLY",
                        "external mutation/spend cannot auto-trigger",
                    )
                )
        indirect_target = _indirect_manual_only_target(text, path.name)
        if indirect_target is not None:
            findings.append(
                WorkflowSecurityFinding(
                    relative,
                    "INDIRECT_MANUAL_ONLY",
                    f"workflow may not proxy-dispatch manual-only target {indirect_target}",
                )
            )
    return tuple(findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args(argv)
    findings = audit_repository(Path(args.repository_root).resolve())
    if not findings:
        print("Repository-wide GitHub Actions security audit PASS")
        return 0
    for finding in findings:
        print(f"BLOCK {finding.rule} {finding.path}: {finding.detail}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

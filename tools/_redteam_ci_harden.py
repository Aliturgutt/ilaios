from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"

PINS = {
    "actions/checkout@v4": "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
    "actions/setup-python@v5": "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
    "actions/setup-node@v4": "actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020",
    "actions/upload-artifact@v4": "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
    "actions/download-artifact@v4": "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093",
    "aws-actions/configure-aws-credentials@v4": "aws-actions/configure-aws-credentials@7474bc4690e29a8392af63c5b98e7449536d5c3a",
    "opentofu/setup-opentofu@v1": "opentofu/setup-opentofu@9d84900f3238fab8cd84ce47d658d25dd008be2f",
}


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def replace_on(path: Path, body: str) -> None:
    text = path.read_text(encoding="utf-8")
    updated, count = re.subn(
        r"(?ms)^on:\n.*?^permissions:",
        f"on:\n{body}\npermissions:",
        text,
        count=1,
    )
    if count != 1:
        raise RuntimeError(f"unable to replace trigger block: {path}")
    write(path, updated)


def harden_checkout_blocks(text: str) -> str:
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if "uses: actions/checkout@" not in lines[i]:
            i += 1
            continue
        uses_indent = len(lines[i]) - len(lines[i].lstrip())
        step_indent = uses_indent if lines[i].lstrip().startswith("- uses:") else max(0, uses_indent - 2)
        end = i + 1
        while end < len(lines):
            stripped = lines[end].lstrip()
            indent = len(lines[end]) - len(stripped)
            if indent == step_indent and stripped.startswith("- "):
                break
            end += 1
        block = lines[i:end]
        with_index = next((n for n, line in enumerate(block) if line.strip() == "with:"), None)
        has_ref = any(line.strip().startswith("ref:") for line in block)
        has_persist = any(line.strip() == "persist-credentials: false" for line in block)
        additions: list[str] = []
        if not has_ref:
            additions.append(" " * (step_indent + 4) + "ref: ${{ github.event.pull_request.head.sha || github.sha }}")
        if not has_persist:
            additions.append(" " * (step_indent + 4) + "persist-credentials: false")
        if additions:
            if with_index is None:
                insert_at = i + 1
                lines[insert_at:insert_at] = [" " * (step_indent + 2) + "with:", *additions]
            else:
                insert_at = i + with_index + 1
                lines[insert_at:insert_at] = additions
            i = insert_at + len(additions) + 1
        else:
            i = end
    return "\n".join(lines) + "\n"


def pin_and_harden_all() -> None:
    for path in sorted(WORKFLOWS.glob("*.yml")):
        if path.name.startswith("_redteam-"):
            continue
        text = path.read_text(encoding="utf-8")
        for old, new in PINS.items():
            text = text.replace(old, new)
        write(path, harden_checkout_blocks(text))


def harden_triggers() -> None:
    for name in (
        "aws-r01-canary-apply.yml",
        "aws-r01-image-scan.yml",
        "aws-r01-preparation-resources.yml",
        "aws-r02-limited-apply.yml",
        "aws-r03-production-apply.yml",
        "video-provider-production-certification.yml",
    ):
        replace_on(WORKFLOWS / name, "  workflow_dispatch:\n")

    replace_on(WORKFLOWS / "platform-ci.yml", "  workflow_call:\n  workflow_dispatch:\n")
    replace_on(WORKFLOWS / "website-ci.yml", "  workflow_call:\n  workflow_dispatch:\n")


def harden_required_gate() -> None:
    path = WORKFLOWS / "required-ci-gate.yml"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "on:\n  pull_request:\n  workflow_dispatch:\n",
        "on:\n  pull_request:\n  push:\n    branches: [master]\n  workflow_dispatch:\n",
        1,
    )
    text = text.replace(
        "          python -m services.desktop_ci_supply_chain --repository-root .\n",
        "          python -m services.desktop_ci_supply_chain --repository-root .\n"
        "          python -m services.github_workflow_security_audit --repository-root .\n",
        1,
    )
    text = text.replace(
        "|.github/workflows/platform-ci.yml|.github/workflows/required-ci-gate.yml|.github/workflows/desktop-*.yml)",
        "|.github/workflows/*.yml)",
        1,
    )
    malware_job = (
        "  malware:\n"
        "    name: Repository malware scan\n"
        "    uses: ./.github/workflows/malware-scan.yml\n\n"
    )
    if "  malware:\n" not in text:
        text = text.replace("  required-ci-gate:\n", malware_job + "  required-ci-gate:\n", 1)
    text = text.replace(
        "needs: [classify, supply-chain, secret-scan, db-migration-safety, api-contract-safety, operational-safety, assurance, final-closure-structure, platform, website]",
        "needs: [classify, supply-chain, secret-scan, db-migration-safety, api-contract-safety, operational-safety, assurance, final-closure-structure, malware, platform, website]",
        1,
    )
    if "MALWARE_RESULT:" not in text:
        text = text.replace(
            "          FINAL_CLOSURE_STRUCTURE_RESULT: ${{ needs.final-closure-structure.result }}\n",
            "          FINAL_CLOSURE_STRUCTURE_RESULT: ${{ needs.final-closure-structure.result }}\n"
            "          MALWARE_RESULT: ${{ needs.malware.result }}\n",
            1,
        )
    if "Repository malware scan failed" not in text:
        text = text.replace(
            '          if [[ "$PLATFORM_REQUIRED" == "true" && "$PLATFORM_RESULT" != "success" ]]; then\n',
            '          if [[ "$MALWARE_RESULT" != "success" ]]; then\n'
            '            echo "Repository malware scan failed: $MALWARE_RESULT"\n'
            "            exit 1\n"
            "          fi\n\n"
            '          if [[ "$PLATFORM_REQUIRED" == "true" && "$PLATFORM_RESULT" != "success" ]]; then\n',
            1,
        )
    write(path, text)


def harden_platform_and_desktop() -> None:
    platform = WORKFLOWS / "platform-ci.yml"
    text = platform.read_text(encoding="utf-8")
    if "group: platform-ci-" not in text:
        text = text.replace(
            "permissions:\n  contents: read\n\njobs:",
            "permissions:\n  contents: read\n\nconcurrency:\n"
            "  group: platform-ci-${{ github.workflow }}-${{ github.ref }}\n"
            "  cancel-in-progress: true\n\njobs:",
            1,
        )
    if "Verify pre-commit checks did not mutate source" not in text:
        text = text.replace(
            "      - name: Diff hygiene\n        run: git diff --check\n",
            "      - name: Verify pre-commit checks did not mutate source\n"
            "        run: git diff --exit-code\n\n"
            "      - name: Diff hygiene\n"
            "        run: git diff --check\n",
            1,
        )
    write(platform, text)

    for name, group in {
        "desktop-ci.yml": "desktop-ci",
        "desktop-msix-packaging.yml": "desktop-msix-packaging",
        "desktop-windows-release.yml": "desktop-windows-gate",
    }.items():
        path = WORKFLOWS / name
        text = path.read_text(encoding="utf-8")
        if f"group: {group}-" not in text:
            text = text.replace(
                "permissions:\n  contents: read\n\njobs:",
                "permissions:\n  contents: read\n\nconcurrency:\n"
                f"  group: {group}-${{{{ github.event.pull_request.number || github.ref }}}}\n"
                "  cancel-in-progress: true\n\njobs:",
                1,
            )
        if name == "desktop-ci.yml":
            if "runs-on: ubuntu-latest\n    timeout-minutes:" not in text:
                text = text.replace("    runs-on: ubuntu-latest\n", "    runs-on: ubuntu-latest\n    timeout-minutes: 30\n", 1)
            if "runs-on: windows-latest\n    timeout-minutes:" not in text:
                text = text.replace("    runs-on: windows-latest\n", "    runs-on: windows-latest\n    timeout-minutes: 45\n", 1)
        write(path, text)

    prod = WORKFLOWS / "website-production-certification.yml"
    text = prod.read_text(encoding="utf-8").replace("          python -m pip install --upgrade pip\n", "")
    write(prod, text)


def create_security_audit() -> None:
    module = '''"""Repository-wide deterministic GitHub Actions security audit."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

_SHA = re.compile(r"^[0-9a-f]{40}$")
_USES = re.compile(r"^\\s*-?\\s*uses:\\s*([^#\\s]+)")
_TOP_PUSH = re.compile(r"(?m)^  push:\\s*$")
_TOP_PR = re.compile(r"(?m)^  pull_request:\\s*$")
_MANUAL_ONLY = frozenset({
    "aws-r01-canary-apply.yml", "aws-r01-image-publish.yml",
    "aws-r01-image-scan.yml", "aws-r01-preparation-resources.yml",
    "aws-r02-limited-apply.yml", "aws-r03-production-apply.yml",
    "desktop-msix-signed-release.yml", "video-provider-production-certification.yml",
})
_SECRET_ALLOWED = frozenset({
    "desktop-msix-signed-release.yml", "video-provider-production-certification.yml",
})

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
        step_indent = uses_indent if line.lstrip().startswith("- uses:") else max(0, uses_indent - 2)
        block = [line]
        for candidate in lines[index + 1:]:
            stripped = candidate.lstrip()
            indent = len(candidate) - len(stripped)
            if indent == step_indent and stripped.startswith("- "):
                break
            block.append(candidate)
        result.append("\\n".join(block))
    return tuple(result)


def audit_repository(repository_root: Path) -> tuple[WorkflowSecurityFinding, ...]:
    findings: list[WorkflowSecurityFinding] = []
    for path in sorted((repository_root / ".github" / "workflows").glob("*.yml")):
        if path.name.startswith("_redteam-"):
            continue
        relative = path.relative_to(repository_root).as_posix()
        text = path.read_text(encoding="utf-8")
        if "pull_request_target:" in text:
            findings.append(WorkflowSecurityFinding(relative, "NO_PR_TARGET", "pull_request_target is forbidden"))
        if "permissions: write-all" in text or re.search(r"(?m)^  contents:\\s+write\\s*$", text):
            findings.append(WorkflowSecurityFinding(relative, "NO_REPO_WRITE", "permanent workflows may not grant contents write"))
        if not re.search(r"(?m)^  contents:\\s+read\\s*$", text):
            findings.append(WorkflowSecurityFinding(relative, "CONTENTS_READ", "explicit contents: read is required"))
        if "secrets." in text and path.name not in _SECRET_ALLOWED:
            findings.append(WorkflowSecurityFinding(relative, "SECRET_BOUNDARY", "secrets are forbidden in this workflow"))
        for line in text.splitlines():
            match = _USES.match(line)
            if match is None:
                continue
            reference = match.group(1)
            if reference.startswith("./"):
                continue
            _, sep, revision = reference.partition("@")
            if not sep or _SHA.fullmatch(revision) is None:
                findings.append(WorkflowSecurityFinding(relative, "IMMUTABLE_ACTION", reference))
        for block in _checkout_blocks(text):
            if "persist-credentials: false" not in block:
                findings.append(WorkflowSecurityFinding(relative, "CHECKOUT_CREDENTIALS", "checkout credentials must not persist"))
            if "ref:" not in block:
                findings.append(WorkflowSecurityFinding(relative, "EXACT_CHECKOUT", "checkout requires explicit exact ref"))
        if path.name in _MANUAL_ONLY:
            if "workflow_dispatch:" not in text:
                findings.append(WorkflowSecurityFinding(relative, "MANUAL_ONLY", "workflow_dispatch is required"))
            if _TOP_PUSH.search(text) or _TOP_PR.search(text):
                findings.append(WorkflowSecurityFinding(relative, "MANUAL_ONLY", "external mutation/spend cannot auto-trigger"))
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
'''
    write(ROOT / "services" / "github_workflow_security_audit.py", module)

    tests = '''from pathlib import Path

from services.github_workflow_security_audit import audit_repository


def _write(root: Path, name: str, body: str) -> None:
    path = root / ".github" / "workflows" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def test_repository_workflow_security_policy_passes_current_tree() -> None:
    assert audit_repository(Path.cwd()) == ()


def test_mutable_action_is_blocked(tmp_path: Path) -> None:
    _write(tmp_path, "validation.yml", "on:\\n  workflow_dispatch:\\npermissions:\\n  contents: read\\njobs:\\n  test:\\n    runs-on: ubuntu-latest\\n    steps:\\n      - uses: actions/checkout@v4\\n        with:\\n          ref: ${{ github.sha }}\\n          persist-credentials: false\\n")
    assert any(item.rule == "IMMUTABLE_ACTION" for item in audit_repository(tmp_path))


def test_external_mutation_push_trigger_is_blocked(tmp_path: Path) -> None:
    _write(tmp_path, "aws-r03-production-apply.yml", "on:\\n  push:\\n    branches: [master]\\n  workflow_dispatch:\\npermissions:\\n  contents: read\\njobs: {}\\n")
    assert any(item.rule == "MANUAL_ONLY" for item in audit_repository(tmp_path))
'''
    write(ROOT / "tests" / "test_github_workflow_security_audit.py", tests)


def create_malware_workflow() -> None:
    malware = '''name: Repository Malware Scan

on:
  workflow_call:
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: malware-scan-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true

jobs:
  clamav:
    name: ClamAV repository scan
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - name: Checkout exact source commit
        uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4
        with:
          ref: ${{ github.event.pull_request.head.sha || github.sha }}
          fetch-depth: 0
          persist-credentials: false

      - name: Install and refresh ClamAV signatures
        shell: bash
        run: |
          set -euo pipefail
          sudo apt-get update
          sudo apt-get install -y --no-install-recommends clamav clamav-freshclam
          sudo systemctl stop clamav-freshclam.service 2>/dev/null || true
          sudo freshclam --stdout
          find /var/lib/clamav -maxdepth 1 -type f \\( -name '*.cvd' -o -name '*.cld' \\) -print | grep -q .
          clamscan --version

      - name: Scan complete repository working tree
        shell: bash
        run: |
          set -euo pipefail
          clamscan --recursive --infected --no-summary --exclude-dir='^./.git$' .
          echo 'ILAIOS_REPOSITORY_MALWARE_SCAN=PASS'
'''
    write(WORKFLOWS / "malware-scan.yml", malware)


def verify_external_actions_pinned() -> None:
    sha = re.compile(r"^[0-9a-f]{40}$")
    uses = re.compile(r"^\s*-?\s*uses:\s*([^#\s]+)")
    failures: list[str] = []
    for path in sorted(WORKFLOWS.glob("*.yml")):
        if path.name.startswith("_redteam-"):
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            match = uses.match(line)
            if match is None:
                continue
            reference = match.group(1)
            if reference.startswith("./"):
                continue
            _, sep, revision = reference.partition("@")
            if not sep or sha.fullmatch(revision) is None:
                failures.append(f"{path.relative_to(ROOT)}: {reference}")
    if failures:
        raise RuntimeError("unpinned actions remain:\n" + "\n".join(failures))


def cleanup_bootstrap() -> None:
    for path in (
        WORKFLOWS / "_redteam-ci-hardening-bootstrap.yml",
        WORKFLOWS / "_redteam-runner-test.yml",
        ROOT / "tools" / "_redteam_ci_harden.py",
        ROOT / ".redteam-ci-hardening-trigger",
    ):
        if path.exists():
            path.unlink()


def main() -> None:
    pin_and_harden_all()
    harden_triggers()
    harden_required_gate()
    harden_platform_and_desktop()
    create_security_audit()
    create_malware_workflow()
    verify_external_actions_pinned()
    cleanup_bootstrap()


if __name__ == "__main__":
    main()

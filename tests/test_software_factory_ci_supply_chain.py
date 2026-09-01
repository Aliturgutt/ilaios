"""SF-18 CI supply-chain hardening policy tests."""

from __future__ import annotations

from pathlib import Path

from services.software_factory_ci_supply_chain import (
    CRITICAL_WORKFLOWS,
    PLATFORM_REQUIREMENTS,
    PRE_COMMIT_CONFIG,
    WEBSITE_REQUIREMENTS,
    SoftwareFactoryCISupplyChainHardening,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKOUT_SHA = "1" * 40
SETUP_SHA = "2" * 40
PRECOMMIT_SHA = "3" * 40


def _checkout() -> str:
    return f"""      - name: Checkout exact source commit
        uses: actions/checkout@{CHECKOUT_SHA}
        with:
          ref: ${{{{ github.event.pull_request.head.sha || github.sha }}}}
          persist-credentials: false
"""


def _required_workflow() -> str:
    return f"""name: Required CI Gate
on:
  pull_request:
permissions:
  contents: read
jobs:
  classify:
    runs-on: ubuntu-latest
    steps:
{_checkout()}  supply-chain:
    runs-on: ubuntu-latest
    steps:
{_checkout()}      - run: python services/software_factory_ci_supply_chain.py --repository-root .
  platform:
    uses: ./.github/workflows/platform-ci.yml
  website:
    uses: ./.github/workflows/website-ci.yml
  required-ci-gate:
    needs: [classify, supply-chain, platform, website]
    runs-on: ubuntu-latest
    steps:
      - env:
          SUPPLY_CHAIN_RESULT: ${{{{ needs.supply-chain.result }}}}
        run: test \"$SUPPLY_CHAIN_RESULT\" = success
"""


def _platform_workflow() -> str:
    return f"""name: Platform CI
on:
  workflow_call:
permissions:
  contents: read
jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
{_checkout()}      - uses: actions/setup-python@{SETUP_SHA}
      - run: python -m pip install --disable-pip-version-check -r {PLATFORM_REQUIREMENTS}
"""


def _website_workflow() -> str:
    return f"""name: Website CI
on:
  workflow_call:
permissions:
  contents: read
jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
{_checkout()}      - uses: actions/setup-node@{SETUP_SHA}
      - run: npm ci --ignore-scripts --audit=false --fund=false
      - run: python -m pip install --disable-pip-version-check -r {WEBSITE_REQUIREMENTS}
"""


def _pre_commit() -> str:
    return f"""repos:
  - repo: https://github.com/example/tool
    rev: {PRECOMMIT_SHA}
    hooks:
      - id: tool
        additional_dependencies:
          - types-example==1.2.3
"""


def _write_fixture(root: Path) -> None:
    values = {
        CRITICAL_WORKFLOWS[0]: _required_workflow(),
        CRITICAL_WORKFLOWS[1]: _platform_workflow(),
        CRITICAL_WORKFLOWS[2]: _website_workflow(),
        PRE_COMMIT_CONFIG: _pre_commit(),
        PLATFORM_REQUIREMENTS: "pytest==9.1.1\nruff==0.1.9\n",
        WEBSITE_REQUIREMENTS: "pytest==9.1.1\n",
    }
    for relative, content in values.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _audit(root: Path):  # type: ignore[no-untyped-def]
    return SoftwareFactoryCISupplyChainHardening().audit(root)


def test_repository_critical_ci_surface_is_hardened() -> None:
    report = _audit(REPO_ROOT)

    assert report.passed is True
    assert report.findings == ()
    assert report.acceptance_authorized is False
    assert report.promotion_authorized is False
    assert report.deployment_authorized is False
    assert report.production_applied is False
    assert report.subject_mutated is False
    assert len(report.report_sha256) == 64


def test_hardening_report_is_deterministic(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    first = _audit(tmp_path)
    second = _audit(tmp_path)

    assert first == second
    assert first.passed is True


def test_mutable_external_action_is_blocked(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    path = tmp_path / CRITICAL_WORKFLOWS[1]
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            f"actions/setup-python@{SETUP_SHA}", "actions/setup-python@v5"
        ),
        encoding="utf-8",
    )

    report = _audit(tmp_path)
    assert report.passed is False
    assert "SF18-MUTABLE-ACTION" in {item.finding_id for item in report.findings}


def test_checkout_credentials_must_not_persist(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    path = tmp_path / CRITICAL_WORKFLOWS[0]
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "persist-credentials: false", "persist-credentials: true", 1
        ),
        encoding="utf-8",
    )

    report = _audit(tmp_path)
    assert "SF18-CHECKOUT-CREDENTIALS" in {
        item.finding_id for item in report.findings
    }


def test_checkout_must_bind_exact_commit_sha(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    path = tmp_path / CRITICAL_WORKFLOWS[2]
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "github.event.pull_request.head.sha || github.sha", "github.ref_name"
        ),
        encoding="utf-8",
    )

    report = _audit(tmp_path)
    assert "SF18-CHECKOUT-NONEXACT-REF" in {
        item.finding_id for item in report.findings
    }


def test_pull_request_target_and_secrets_are_blocked(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    path = tmp_path / CRITICAL_WORKFLOWS[0]
    path.write_text(
        path.read_text(encoding="utf-8")
        .replace("pull_request:", "pull_request_target:")
        .replace("run: test", "env:\n          TOKEN: ${{ secrets.PROD_TOKEN }}\n        run: test"),
        encoding="utf-8",
    )

    report = _audit(tmp_path)
    ids = {item.finding_id for item in report.findings}
    assert "SF18-PR-TARGET" in ids
    assert "SF18-PR-SECRETS" in ids


def test_write_scoped_github_token_is_blocked(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    path = tmp_path / CRITICAL_WORKFLOWS[1]
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "contents: read", "contents: read\n  packages: write"
        ),
        encoding="utf-8",
    )

    report = _audit(tmp_path)
    assert "SF18-WRITE-TOKEN" in {item.finding_id for item in report.findings}


def test_untrusted_pr_text_interpolation_is_blocked(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    path = tmp_path / CRITICAL_WORKFLOWS[0]
    path.write_text(
        path.read_text(encoding="utf-8")
        + "\n      - run: echo '${{ github.event.pull_request.title }}'\n",
        encoding="utf-8",
    )

    report = _audit(tmp_path)
    assert "SF18-UNTRUSTED-RUN-INTERPOLATION" in {
        item.finding_id for item in report.findings
    }


def test_precommit_revisions_and_additional_dependencies_are_immutable(
    tmp_path: Path,
) -> None:
    _write_fixture(tmp_path)
    path = tmp_path / PRE_COMMIT_CONFIG
    path.write_text(
        path.read_text(encoding="utf-8")
        .replace(PRECOMMIT_SHA, "v1.2.3")
        .replace("types-example==1.2.3", "types-example"),
        encoding="utf-8",
    )

    report = _audit(tmp_path)
    ids = {item.finding_id for item in report.findings}
    assert "SF18-MUTABLE-PRECOMMIT-REV" in ids
    assert "SF18-FLOATING-PRECOMMIT-DEPENDENCY" in ids


def test_ci_requirement_locks_reject_floating_versions(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    path = tmp_path / PLATFORM_REQUIREMENTS
    path.write_text("pytest>=9\nruff==0.1.9\n", encoding="utf-8")

    report = _audit(tmp_path)
    assert "SF18-FLOATING-REQUIREMENT" in {
        item.finding_id for item in report.findings
    }


def test_required_gate_cannot_omit_supply_chain_result(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    path = tmp_path / CRITICAL_WORKFLOWS[0]
    path.write_text(
        path.read_text(encoding="utf-8").replace("SUPPLY_CHAIN_RESULT", "CHAIN_RESULT"),
        encoding="utf-8",
    )

    report = _audit(tmp_path)
    assert "SF18-GATE-NOT-AGGREGATED" in {
        item.finding_id for item in report.findings
    }


def test_platform_ci_cannot_restore_floating_pip_upgrade(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    path = tmp_path / CRITICAL_WORKFLOWS[1]
    path.write_text(
        path.read_text(encoding="utf-8") + "\n      - run: pip install --upgrade pip\n",
        encoding="utf-8",
    )

    report = _audit(tmp_path)
    assert "SF18-FLOATING-PIP-UPGRADE" in {
        item.finding_id for item in report.findings
    }

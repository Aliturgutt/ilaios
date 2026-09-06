from __future__ import annotations

from pathlib import Path

import pytest

from services.runtime.security_agent_adapters import (
    CODESEC_ADAPTER_KIND,
    INFRASTRUCTURE_ADAPTER_KIND,
    SUPPLY_CHAIN_ADAPTER_KIND,
    SecurityAgentRuntimeAdapters,
)
from services.security_methodology_analysis import (
    SecurityMethodologyAnalysisError,
    SecurityMethodologyAnalyzer,
)
from services.security_methodology_skills import (
    AGENTIC_ACTION_AUDIT_SKILL_ID,
    DIFFERENTIAL_REVIEW_SKILL_ID,
    SECURITY_METHODOLOGY_SKILLS,
    SUPPLY_CHAIN_AUDIT_SKILL_ID,
    THREAT_MODEL_SKILL_ID,
    default_security_methodology_skills_root,
    definition_for,
)
from services.security_factory import SecurityScope

ROOT = Path(__file__).resolve().parents[1]
_SHA_A = "a" * 40
_SHA_B = "b" * 40


def _scope(root: Path) -> SecurityScope:
    return SecurityScope("methodology-test", root)


def _skill_metadata(skill_id: str) -> dict[str, object]:
    return {
        "_ilaios_skill": {
            "skill_id": skill_id,
            "sha256": "0" * 64,
            "instructions": "test",
        }
    }


def test_security_methodology_registry_contains_exact_first_party_packages() -> None:
    skills_root = default_security_methodology_skills_root(ROOT)
    expected = {item.skill_id for item in SECURITY_METHODOLOGY_SKILLS}
    discovered = {
        path.name
        for path in skills_root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    }
    assert discovered == expected
    assert len(expected) == 6
    for skill_id in expected:
        definition = definition_for(skill_id)
        assert definition is not None
        assert (skills_root / skill_id / "SKILL.md").is_file()
        provenance = (
            skills_root / skill_id / "PROVENANCE.md"
        ).read_text(encoding="utf-8")
        assert "CODE/TEXT IMPORTED = NONE" in provenance


def test_differential_review_rejects_scope_escape_and_marks_test_gap(
    tmp_path: Path,
) -> None:
    (tmp_path / "services").mkdir()
    (tmp_path / "services" / "policy.py").write_text(
        "value = 1\n",
        encoding="utf-8",
    )
    analyzer = SecurityMethodologyAnalyzer()
    scope = _scope(tmp_path)

    with pytest.raises(
        SecurityMethodologyAnalysisError,
        match="escapes repository scope",
    ):
        analyzer.differential_review(
            scope,
            base_sha=_SHA_A,
            head_sha=_SHA_B,
            changed_paths=("../outside.py",),
        )

    report = analyzer.differential_review(
        scope,
        base_sha=_SHA_A,
        head_sha=_SHA_B,
        changed_paths=("services/policy.py",),
    )
    assert {
        item.finding_id for item in report.findings
    } == {"DIFF-PROTECTED-CHANGE-WITHOUT-TEST-EVIDENCE"}
    assert report.passed is True


def test_agentic_action_audit_detects_privileged_untrusted_ai_flow(
    tmp_path: Path,
) -> None:
    workflow_root = tmp_path / ".github" / "workflows"
    workflow_root.mkdir(parents=True)
    (workflow_root / "review.yml").write_text(
        """
name: review
on:
  pull_request_target:
permissions:
  contents: write
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: openai/codex-action@v1
        with:
          sandbox: danger-full-access
          prompt: ${{ github.event.pull_request.title }}
""".lstrip(),
        encoding="utf-8",
    )

    report = SecurityMethodologyAnalyzer().audit_agentic_actions(
        _scope(tmp_path)
    )
    ids = {item.finding_id for item in report.findings}
    assert {
        "AGENTIC-PR-TARGET",
        "AGENTIC-BROAD-WRITE-PERMISSION",
        "AGENTIC-UNSAFE-EXECUTION-MODE",
        "AGENTIC-UNTRUSTED-EVENT-TO-PROMPT",
    } <= ids
    assert report.passed is False


def test_supply_chain_audit_flags_mutable_action_and_latest_image(
    tmp_path: Path,
) -> None:
    workflow_root = tmp_path / ".github" / "workflows"
    workflow_root.mkdir(parents=True)
    (workflow_root / "ci.yml").write_text(
        "jobs:\n  test:\n    steps:\n      - uses: actions/checkout@v4\n",
        encoding="utf-8",
    )
    (tmp_path / "Dockerfile").write_text(
        "FROM python:latest\n",
        encoding="utf-8",
    )

    report = SecurityMethodologyAnalyzer().supply_chain_audit(
        _scope(tmp_path)
    )
    ids = {item.finding_id for item in report.findings}
    assert "SUPPLY-GHA-MUTABLE-REF" in ids
    assert "SUPPLY-DOCKER-LATEST" in ids
    assert report.passed is True


def test_supply_chain_audit_accepts_immutable_action_and_container_digest(
    tmp_path: Path,
) -> None:
    workflow_root = tmp_path / ".github" / "workflows"
    workflow_root.mkdir(parents=True)
    (workflow_root / "ci.yml").write_text(
        "jobs:\n  test:\n    steps:\n      - uses: actions/checkout@"
        + ("a" * 40)
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "Dockerfile").write_text(
        "FROM python:3.13@sha256:" + ("b" * 64) + "\n",
        encoding="utf-8",
    )

    report = SecurityMethodologyAnalyzer().supply_chain_audit(
        _scope(tmp_path)
    )
    ids = {item.finding_id for item in report.findings}
    assert "SUPPLY-GHA-MUTABLE-REF" not in ids
    assert "SUPPLY-GHA-UNVERSIONED-ACTION" not in ids
    assert "SUPPLY-DOCKER-LATEST" not in ids


def test_threat_model_reports_evidence_gaps_without_calling_them_exploits(
    tmp_path: Path,
) -> None:
    (tmp_path / "identity.py").write_text("user_id = 'x'\n", encoding="utf-8")
    report, surface = SecurityMethodologyAnalyzer().threat_model(
        _scope(tmp_path)
    )
    assert surface["identity_and_authentication"] == ("identity.py",)
    assert any(
        item.finding_id.startswith("THREAT-MODEL-MISSING-")
        for item in report.findings
    )
    assert all(item.severity.name == "MEDIUM" for item in report.findings)
    assert report.passed is True


def test_runtime_adapters_dispatch_only_to_owned_methodology_skills(
    tmp_path: Path,
) -> None:
    workflow_root = tmp_path / ".github" / "workflows"
    workflow_root.mkdir(parents=True)
    (workflow_root / "ai.yml").write_text(
        "jobs:\n  audit:\n    steps:\n      - uses: openai/codex-action@v1\n",
        encoding="utf-8",
    )
    adapters = SecurityAgentRuntimeAdapters().runtime_adapters()

    infra = adapters[INFRASTRUCTURE_ADAPTER_KIND](
        {
            "scope_id": "agentic",
            "repository_root": str(tmp_path),
            **_skill_metadata(AGENTIC_ACTION_AUDIT_SKILL_ID),
        }
    )
    assert infra["scope_id"] == "agentic"

    supply = adapters[SUPPLY_CHAIN_ADAPTER_KIND](
        {
            "scope_id": "supply",
            "repository_root": str(tmp_path),
            **_skill_metadata(SUPPLY_CHAIN_AUDIT_SKILL_ID),
        }
    )
    assert supply["scope_id"] == "supply"

    threat = adapters[CODESEC_ADAPTER_KIND](
        {
            "scope_id": "threat",
            "repository_root": str(tmp_path),
            **_skill_metadata(THREAT_MODEL_SKILL_ID),
        }
    )
    assert "threat_surface" in threat

    differential = adapters[CODESEC_ADAPTER_KIND](
        {
            "scope_id": "diff",
            "repository_root": str(tmp_path),
            "base_sha": _SHA_A,
            "head_sha": _SHA_B,
            "changed_paths": [".github/workflows/ai.yml"],
            **_skill_metadata(DIFFERENTIAL_REVIEW_SKILL_ID),
        }
    )
    assert differential["scope_id"] == "diff"


def test_infrastructure_adapter_surfaces_blocking_container_root_finding(
    tmp_path: Path,
) -> None:
    (tmp_path / "Dockerfile").write_text(
        "FROM python:3.13\nUSER root\n",
        encoding="utf-8",
    )

    report = SecurityAgentRuntimeAdapters().runtime_adapters()[
        INFRASTRUCTURE_ADAPTER_KIND
    ](
        {
            "scope_id": "container-root",
            "repository_root": str(tmp_path),
        }
    )

    assert report["passed"] is False
    assert report["blocking_finding_count"] == 1
    assert {
        item["finding_id"] for item in report["findings"]
    } == {"CONTAINER-ROOT-USER"}
    assert {
        item["category"] for item in report["findings"]
    } == {"container"}


def test_infrastructure_adapter_keeps_non_root_container_clean(
    tmp_path: Path,
) -> None:
    (tmp_path / "Dockerfile").write_text(
        "FROM python:3.13\nUSER 10001\n",
        encoding="utf-8",
    )

    report = SecurityAgentRuntimeAdapters().runtime_adapters()[
        INFRASTRUCTURE_ADAPTER_KIND
    ](
        {
            "scope_id": "container-non-root",
            "repository_root": str(tmp_path),
        }
    )

    assert report["passed"] is True
    assert report["blocking_finding_count"] == 0
    assert all(
        item["finding_id"] != "CONTAINER-ROOT-USER"
        for item in report["findings"]
    )

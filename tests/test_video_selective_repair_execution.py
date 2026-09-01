from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest

from services.integrations.video_repair import GovernedSelectiveRepairExecutor
from services.integrations.video_skill_governance import approve_video_skills
from services.runtime.routing import AgentProfile, RuntimeError, SkillRegistry
from src.video_automation.selective_repair_execution import (
    SelectiveRepairExecutionCoordinator,
    SelectiveRepairExecutionError,
)
from src.video_automation.video_skills import RepairRequest


class _WritingRepairAction:
    def __init__(self, *, change_output: bool = True) -> None:
        self.calls = 0
        self._change_output = change_output

    @property
    def executor_id(self) -> str:
        return "test-repair-action-v1"

    def execute(
        self,
        request: RepairRequest,
        *,
        source_path: Path,
        output_path: Path,
    ) -> None:
        self.calls += 1
        body = source_path.read_bytes()
        output_path.write_bytes(
            body + f"|repaired:{request.target}".encode("utf-8")
            if self._change_output
            else body
        )


class _NoOutputRepairAction:
    @property
    def executor_id(self) -> str:
        return "no-output-repair-v1"

    def execute(
        self,
        request: RepairRequest,
        *,
        source_path: Path,
        output_path: Path,
    ) -> None:
        return None


def _registry() -> SkillRegistry:
    registry = SkillRegistry()
    approve_video_skills(registry)
    return registry


def _source(tmp_path: Path) -> tuple[Path, bytes, str]:
    body = b"video-before-repair"
    path = tmp_path / "source.mp4"
    path.write_bytes(body)
    return path, body, sha256(body).hexdigest()


def _request() -> RepairRequest:
    return RepairRequest(
        repair_id="repair:finding:brand:1",
        finding_id="finding:brand",
        target="scene:brand",
        attempt=1,
    )


def test_repair_execution_is_bound_to_exact_source_and_target(tmp_path: Path) -> None:
    source, body, source_sha = _source(tmp_path)
    action = _WritingRepairAction()
    evidence = SelectiveRepairExecutionCoordinator(action).execute(
        _request(),
        source_path=source,
        source_artifact_sha256=source_sha,
        source_byte_length=len(body),
        output_directory=tmp_path / "repairs",
        provenance_reference="qa-run:video-qa-001",
    )
    assert action.calls == 1
    assert evidence.repair_id == _request().repair_id
    assert evidence.finding_id == _request().finding_id
    assert evidence.target == _request().target
    assert evidence.source_artifact_sha256 == source_sha
    assert evidence.output_artifact_sha256 != source_sha
    assert evidence.output_byte_length == Path(evidence.output_path).stat().st_size
    assert evidence.provenance_reference == "qa-run:video-qa-001"


def test_repair_rejects_source_sha_substitution_before_action(tmp_path: Path) -> None:
    source, body, _ = _source(tmp_path)
    action = _WritingRepairAction()
    with pytest.raises(SelectiveRepairExecutionError, match="SHA-256 mismatch"):
        SelectiveRepairExecutionCoordinator(action).execute(
            _request(),
            source_path=source,
            source_artifact_sha256="b" * 64,
            source_byte_length=len(body),
            output_directory=tmp_path / "repairs",
            provenance_reference="qa-run:video-qa-001",
        )
    assert action.calls == 0


def test_repair_rejects_source_length_substitution_before_action(tmp_path: Path) -> None:
    source, body, source_sha = _source(tmp_path)
    action = _WritingRepairAction()
    with pytest.raises(SelectiveRepairExecutionError, match="byte length mismatch"):
        SelectiveRepairExecutionCoordinator(action).execute(
            _request(),
            source_path=source,
            source_artifact_sha256=source_sha,
            source_byte_length=len(body) + 1,
            output_directory=tmp_path / "repairs",
            provenance_reference="qa-run:video-qa-001",
        )
    assert action.calls == 0


def test_repair_rejects_noop_artifact(tmp_path: Path) -> None:
    source, body, source_sha = _source(tmp_path)
    with pytest.raises(SelectiveRepairExecutionError, match="did not change"):
        SelectiveRepairExecutionCoordinator(
            _WritingRepairAction(change_output=False)
        ).execute(
            _request(),
            source_path=source,
            source_artifact_sha256=source_sha,
            source_byte_length=len(body),
            output_directory=tmp_path / "repairs",
            provenance_reference="qa-run:video-qa-001",
        )


def test_repair_rejects_missing_output(tmp_path: Path) -> None:
    source, body, source_sha = _source(tmp_path)
    with pytest.raises(SelectiveRepairExecutionError, match="did not emit"):
        SelectiveRepairExecutionCoordinator(_NoOutputRepairAction()).execute(
            _request(),
            source_path=source,
            source_artifact_sha256=source_sha,
            source_byte_length=len(body),
            output_directory=tmp_path / "repairs",
            provenance_reference="qa-run:video-qa-001",
        )


def test_governed_repair_requires_media_write_authority(tmp_path: Path) -> None:
    source, body, source_sha = _source(tmp_path)
    action = _WritingRepairAction()
    governed = GovernedSelectiveRepairExecutor(
        _registry(),
        AgentProfile("repair-worker", frozenset({"media.read"})),
        SelectiveRepairExecutionCoordinator(action),
    )
    with pytest.raises(RuntimeError, match="expand agent authority"):
        governed.execute(
            _request(),
            source_path=source,
            source_artifact_sha256=source_sha,
            source_byte_length=len(body),
            output_directory=tmp_path / "repairs",
            provenance_reference="qa-run:video-qa-001",
        )
    assert action.calls == 0


def test_governed_repair_delegates_after_authority_validation(tmp_path: Path) -> None:
    source, body, source_sha = _source(tmp_path)
    action = _WritingRepairAction()
    evidence = GovernedSelectiveRepairExecutor(
        _registry(),
        AgentProfile(
            "repair-worker",
            frozenset({"media.read", "media.write"}),
        ),
        SelectiveRepairExecutionCoordinator(action),
    ).execute(
        _request(),
        source_path=source,
        source_artifact_sha256=source_sha,
        source_byte_length=len(body),
        output_directory=tmp_path / "repairs",
        provenance_reference="qa-run:video-qa-001",
    )
    assert action.calls == 1
    assert evidence.executor_id == action.executor_id

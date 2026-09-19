"""RAG.14 operational evidence controls stay bounded and fail closed."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from services.rag14_maintenance import (
    RAG14MaintenanceError,
    _corrupt_archive,
    run_backup_restore_drill,
)


def _repository() -> Path:
    return Path(__file__).resolve().parents[1]


def test_rag14_maintenance_is_canary_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ILAIOS_RELEASE_STATE", "PRODUCTION")
    with pytest.raises(RAG14MaintenanceError, match="CANARY-only"):
        run_backup_restore_drill(tmp_path)


def test_rag14_corrupt_archive_changes_state_without_rewriting_manifest(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.zip"
    target = tmp_path / "target.zip"
    with zipfile.ZipFile(source, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("state.sqlite3", b"state")
        archive.writestr("manifest.json", b'{"format":"ILAIOS_RUNTIME_BACKUP_V1"}')

    _corrupt_archive(source, target)

    with zipfile.ZipFile(source) as original, zipfile.ZipFile(target) as corrupted:
        assert original.read("manifest.json") == corrupted.read("manifest.json")
        assert original.read("state.sqlite3") != corrupted.read("state.sqlite3")


def test_rag14_runtime_routes_only_explicit_maintenance_mode() -> None:
    source = (_repository() / "services/deployment/runtime.py").read_text(
        encoding="utf-8"
    )

    assert "ILAIOS_RAG14_MAINTENANCE_MODE" in source
    assert "rag14_maintenance_main" in source
    assert "if maintenance_mode:" in source


def test_rag14_operational_collector_covers_required_runtime_drills() -> None:
    source = (_repository() / "services/rag14_operational_evidence.py").read_text(
        encoding="utf-8"
    )

    assert '"backup_restore_test"' in source
    assert '"run-task"' in source
    assert '"deployment-health-window.json"' in source
    assert '"observability-alerts.json"' in source
    assert '"finops-resource-meter.json"' in source
    assert '"rollback-recovery.json"' in source
    assert "RAG14_PREVIOUS_TASK_DEFINITION" in source
    assert "Required CI Gate" in source
    assert "production_authority" in source


def test_rag14_operational_collector_defines_all_alert_evidence_rules() -> None:
    source = (_repository() / "services/rag14_operational_evidence.py").read_text(
        encoding="utf-8"
    )
    for label in (
        "embedding-failure",
        "excessive-latency",
        "memory-pressure",
        "retrieval-failure",
        "index-corruption",
        "backup-failure",
        "authorization-anomaly",
        "leakage-security",
    ):
        assert f'"{label}"' in source
    assert '"ALARM"' in source
    assert '"OK"' in source
    assert "delete-alarms" in source


def test_rag14_workflow_requires_operational_evidence_before_upload() -> None:
    workflow = (
        _repository() / ".github/workflows/aws-r01-canary-apply.yml"
    ).read_text(encoding="utf-8")

    operational = workflow.index("python -m services.rag14_operational_evidence")
    upload = workflow.index("name: Preserve RAG.14 canary evidence")
    assert operational < upload
    assert "RAG14_EXTERNAL_SPEND_APPROVED=true" in workflow
    assert "RAG14_PREVIOUS_TASK_DEFINITION" in workflow

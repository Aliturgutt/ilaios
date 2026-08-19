from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from services.governance.gates import GateError
from services.governance.work_evidence import GovernedWorkEvidenceReader


def _database(path: Path) -> Path:
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE governed_work ("
            "request_id TEXT PRIMARY KEY, requester_id TEXT NOT NULL, "
            "agent_id TEXT NOT NULL, skill_id TEXT NOT NULL, "
            "capability TEXT NOT NULL, payload_json TEXT NOT NULL, "
            "secret_ids_json TEXT NOT NULL, status TEXT NOT NULL, result_json TEXT)"
        )
        connection.execute(
            "INSERT INTO governed_work VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "request-1",
                "requester-1",
                "agent-1",
                "skill-1",
                "capability-1",
                '{"secret":"must-not-project"}',
                '["opaque-secret-id"]',
                "executed",
                '{"result":"must-not-project"}',
            ),
        )
    return path


def test_snapshot_projects_only_persisted_identity_and_status(tmp_path: Path) -> None:
    reader = GovernedWorkEvidenceReader(_database(tmp_path / "governance.sqlite3"))
    assert reader.snapshot("request-1") == {
        "request_id": "request-1",
        "requester_id": "requester-1",
        "agent_id": "agent-1",
        "skill_id": "skill-1",
        "capability": "capability-1",
        "status": "executed",
    }


def test_snapshot_fails_closed_for_unknown_request(tmp_path: Path) -> None:
    reader = GovernedWorkEvidenceReader(_database(tmp_path / "governance.sqlite3"))
    with pytest.raises(GateError, match="evidence is unavailable"):
        reader.snapshot("unknown")


def test_snapshot_fails_closed_without_database(tmp_path: Path) -> None:
    reader = GovernedWorkEvidenceReader(tmp_path / "missing.sqlite3")
    with pytest.raises(GateError, match="database is unavailable"):
        reader.snapshot("request-1")

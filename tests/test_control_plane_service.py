"""Runtime boundary and migration tests for PLATFORM.P05 recovery."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, cast
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

import pytest

from services.control_plane.migrations import (
    LATEST_SCHEMA_VERSION,
    MigrationError,
    current_schema_version,
    migrate_database,
    rollback_database,
)


@contextmanager
def _running_service(tmp_path: Path) -> Iterator[tuple[str, subprocess.Popen[str]]]:
    ready_file = tmp_path / "ready.json"
    environment = os.environ.copy()
    environment["ILAIOS_CONTROL_PLANE_TOKEN"] = "runtime-secret"
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "services.control_plane.server",
            "--database",
            str(tmp_path / "state.sqlite3"),
            "--ready-file",
            str(ready_file),
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    deadline = time.monotonic() + 10
    while not ready_file.exists():
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout is not None else ""
            raise AssertionError(f"control-plane process exited early: {output}")
        if time.monotonic() >= deadline:
            process.kill()
            raise AssertionError("control-plane process did not become ready")
        time.sleep(0.01)
    ready = json.loads(ready_file.read_text(encoding="utf-8"))
    assert ready["schema_version"] == LATEST_SCHEMA_VERSION
    try:
        yield f"http://{ready['host']}:{ready['port']}", process
    finally:
        process.terminate()
        process.wait(timeout=10)


def _request(
    base_url: str,
    method: str,
    path: str,
    *,
    token: str = "runtime-secret",
    payload: dict[str, object] | None = None,
) -> tuple[int, dict[str, Any]]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        base_url + path,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        response = urlopen(request, timeout=5)
    except HTTPError as error:
        return error.code, cast(dict[str, Any], json.loads(error.read()))
    with response:
        return response.status, cast(dict[str, Any], json.loads(response.read()))


def test_real_process_boundary_persists_goal_job_and_events_after_restart(
    tmp_path: Path,
) -> None:
    with _running_service(tmp_path) as (base_url, first_process):
        assert first_process.poll() is None
        status, goal = _request(
            base_url,
            "POST",
            "/v1/goals",
            payload={"objective": "Execute a persistent governed goal"},
        )
        assert status == 201
        status, job = _request(
            base_url,
            "POST",
            "/v1/jobs",
            payload={"goal_id": goal["goal_id"]},
        )
        assert status == 201

    (tmp_path / "ready.json").unlink()
    with _running_service(tmp_path) as (base_url, second_process):
        assert second_process.pid != first_process.pid
        status, persisted_goal = _request(
            base_url, "GET", f"/v1/goals/{goal['goal_id']}"
        )
        assert status == 200
        assert persisted_goal == goal
        status, persisted_job = _request(
            base_url, "GET", f"/v1/jobs/{job['job_id']}"
        )
        assert status == 200
        assert persisted_job == job
        status, event_payload = _request(base_url, "GET", "/v1/events")
        assert status == 200
        assert [event["event_type"] for event in event_payload["events"]] == [
            "goal.created",
            "job.created",
        ]


def test_process_boundary_rejects_missing_wrong_and_malformed_requests(
    tmp_path: Path,
) -> None:
    with _running_service(tmp_path) as (base_url, _):
        status, payload = _request(base_url, "GET", "/v1/events", token="wrong")
        assert status == 401
        assert payload == {"error": "invalid local bearer token"}
        status, payload = _request(
            base_url, "POST", "/v1/goals", payload={"objective": " "}
        )
        assert status == 400
        assert payload == {"error": "objective must be non-blank and trimmed"}


def test_versioned_migration_and_recoverable_rollback(tmp_path: Path) -> None:
    database = tmp_path / "state.sqlite3"
    backup = tmp_path / "rollback-backup.sqlite3"

    assert migrate_database(database) == LATEST_SCHEMA_VERSION
    assert migrate_database(database) == LATEST_SCHEMA_VERSION
    assert current_schema_version(database) == LATEST_SCHEMA_VERSION
    assert rollback_database(database, backup) == LATEST_SCHEMA_VERSION - 1
    assert backup.is_file()
    assert current_schema_version(database) == LATEST_SCHEMA_VERSION - 1
    assert current_schema_version(backup) == LATEST_SCHEMA_VERSION

    with pytest.raises(MigrationError, match="backup path already exists"):
        rollback_database(backup, backup)


def test_migration_adopts_exact_legacy_schema_without_losing_records(
    tmp_path: Path,
) -> None:
    database = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE goals (
                goal_id TEXT PRIMARY KEY,
                objective TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE jobs (
                job_id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL REFERENCES goals(goal_id),
                state TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE events (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                aggregate_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                schema_version TEXT NOT NULL
            );
            INSERT INTO goals VALUES (
                'goal-00000001', 'preserve me', '2026-08-09T00:00:00+00:00'
            );
            """
        )

    assert migrate_database(database) == LATEST_SCHEMA_VERSION
    with sqlite3.connect(database) as connection:
        row = connection.execute("SELECT objective FROM goals").fetchone()
    assert row == ("preserve me",)


def test_bounded_proposal_crosses_boundary_and_survives_restart(
    tmp_path: Path,
) -> None:
    with _running_service(tmp_path) as (base_url, _):
        _, goal = _request(
            base_url,
            "POST",
            "/v1/goals",
            payload={"objective": "Produce a governed artifact"},
        )
        status, proposal = _request(
            base_url,
            "POST",
            "/v1/proposals",
            payload={
                "goal_id": goal["goal_id"],
                "acceptance_criteria": ["Artifact validates", "Evidence persists"],
                "risk_class": "medium",
                "data_class": "internal",
                "budget": {
                    "max_attempts": 3,
                    "max_runtime_seconds": 600,
                    "max_external_spend_minor": 0,
                },
                "tasks": [
                    {
                        "task_id": "validate",
                        "responsibility": "Validate artifact",
                        "dependencies": ["produce"],
                    },
                    {
                        "task_id": "produce",
                        "responsibility": "Produce artifact",
                        "dependencies": [],
                    },
                ],
            },
        )
        assert status == 201
        assert proposal["topological_order"] == ["produce", "validate"]
        assert proposal["privileged_execution_authorized"] is False

    (tmp_path / "ready.json").unlink()
    with _running_service(tmp_path) as (base_url, _):
        status, persisted = _request(
            base_url, "GET", f"/v1/proposals/{proposal['proposal_id']}"
        )
        assert status == 200
        assert persisted == proposal


def test_invalid_proposal_is_rejected_without_durable_event(tmp_path: Path) -> None:
    with _running_service(tmp_path) as (base_url, _):
        _, goal = _request(
            base_url,
            "POST",
            "/v1/goals",
            payload={"objective": "Reject an unbounded graph"},
        )
        status, rejected = _request(
            base_url,
            "POST",
            "/v1/proposals",
            payload={
                "goal_id": goal["goal_id"],
                "acceptance_criteria": ["Must remain bounded"],
                "risk_class": "high",
                "data_class": "restricted",
                "budget": {
                    "max_attempts": 1,
                    "max_runtime_seconds": 60,
                    "max_external_spend_minor": 0,
                },
                "tasks": [
                    {
                        "task_id": "cycle-a",
                        "responsibility": "A",
                        "dependencies": ["cycle-b"],
                    },
                    {
                        "task_id": "cycle-b",
                        "responsibility": "B",
                        "dependencies": ["cycle-a"],
                    },
                ],
            },
        )
        assert status == 400
        assert rejected == {"error": "task graph must be acyclic"}
        _, events = _request(base_url, "GET", "/v1/events")
        assert [event["event_type"] for event in events["events"]] == [
            "goal.created"
        ]


def test_workflow_crash_retry_duplicate_delivery_and_compensation_cross_boundary(
    tmp_path: Path,
) -> None:
    future = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    with _running_service(tmp_path) as (base_url, _):
        _request(
            base_url,
            "POST",
            "/v1/workflow/commands",
            payload={"operation": "create_workflow", "workflow_id": "workflow-1"},
        )
        _request(
            base_url,
            "POST",
            "/v1/workflow/commands",
            payload={
                "operation": "add_task",
                "workflow_id": "workflow-1",
                "task_id": "render",
                "max_attempts": 2,
            },
        )
        _, attempt = _request(
            base_url,
            "POST",
            "/v1/workflow/commands",
            payload={
                "operation": "begin_attempt",
                "workflow_id": "workflow-1",
                "task_id": "render",
                "deadline": future,
            },
        )
        _request(
            base_url,
            "POST",
            "/v1/workflow/commands",
            payload={
                "operation": "save_checkpoint",
                "attempt_id": attempt["attempt_id"],
                "key": "frame",
                "payload": {"number": 42},
            },
        )

    (tmp_path / "ready.json").unlink()
    with _running_service(tmp_path) as (base_url, _):
        status, checkpoint = _request(
            base_url,
            "GET",
            "/v1/workflow/checkpoint?attempt_id="
            + quote(str(attempt["attempt_id"]))
            + "&key=frame",
        )
        assert status == 200
        assert checkpoint == {"payload": {"number": 42}}
        _, failed = _request(
            base_url,
            "POST",
            "/v1/workflow/commands",
            payload={
                "operation": "fail_attempt",
                "attempt_id": attempt["attempt_id"],
                "reason": "worker process lost",
            },
        )
        assert failed == {"task_status": "ready"}
        _, retry = _request(
            base_url,
            "POST",
            "/v1/workflow/commands",
            payload={
                "operation": "begin_attempt",
                "workflow_id": "workflow-1",
                "task_id": "render",
                "deadline": future,
            },
        )
        assert retry["number"] == 2
        _request(
            base_url,
            "POST",
            "/v1/workflow/commands",
            payload={
                "operation": "complete_attempt",
                "attempt_id": retry["attempt_id"],
            },
        )
        _, received = _request(
            base_url,
            "POST",
            "/v1/workflow/commands",
            payload={
                "operation": "receive_event",
                "event_id": "event-1",
                "payload": {"state": "ready"},
            },
        )
        assert received == {"accepted": True}

    (tmp_path / "ready.json").unlink()
    with _running_service(tmp_path) as (base_url, _):
        _, duplicate = _request(
            base_url,
            "POST",
            "/v1/workflow/commands",
            payload={
                "operation": "receive_event",
                "event_id": "event-1",
                "payload": {"state": "ready"},
            },
        )
        assert duplicate == {"accepted": False}
        _request(
            base_url,
            "POST",
            "/v1/workflow/commands",
            payload={"operation": "create_workflow", "workflow_id": "workflow-2"},
        )
        _request(
            base_url,
            "POST",
            "/v1/workflow/commands",
            payload={
                "operation": "add_task",
                "workflow_id": "workflow-2",
                "task_id": "publish",
                "max_attempts": 1,
                "compensation_event_type": "publication.rollback.requested",
            },
        )
        past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        _, timed_attempt = _request(
            base_url,
            "POST",
            "/v1/workflow/commands",
            payload={
                "operation": "begin_attempt",
                "workflow_id": "workflow-2",
                "task_id": "publish",
                "deadline": past,
            },
        )
        _, timed_out = _request(
            base_url,
            "POST",
            "/v1/workflow/commands",
            payload={
                "operation": "timeout_attempt",
                "attempt_id": timed_attempt["attempt_id"],
                "now": datetime.now(timezone.utc).isoformat(),
            },
        )
        assert timed_out == {"task_status": "failed"}
        _, pending = _request(base_url, "GET", "/v1/workflow/outbox")
        assert pending["events"][0]["event_type"] == "publication.rollback.requested"
        event_id = pending["events"][0]["event_id"]
        _request(
            base_url,
            "POST",
            "/v1/workflow/commands",
            payload={"operation": "acknowledge_outbox", "event_id": event_id},
        )
        _, reconciled = _request(base_url, "GET", "/v1/workflow/outbox")
        assert reconciled == {"events": []}

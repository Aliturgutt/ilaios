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
from pathlib import Path
from typing import Any, cast
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from services.control_plane.migrations import (
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
    assert ready["schema_version"] == 1
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
    payload: dict[str, str] | None = None,
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

    assert migrate_database(database) == 1
    assert migrate_database(database) == 1
    assert current_schema_version(database) == 1
    assert rollback_database(database, backup) == 0
    assert backup.is_file()
    assert current_schema_version(database) == 0
    assert current_schema_version(backup) == 1

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

    assert migrate_database(database) == 1
    with sqlite3.connect(database) as connection:
        row = connection.execute("SELECT objective FROM goals").fetchone()
    assert row == ("preserve me",)

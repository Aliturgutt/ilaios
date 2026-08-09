"""Runtime boundary and migration tests for PLATFORM.P05 recovery."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, cast
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

import pytest

from services.control_plane import LiveEvent, LiveStateError, LiveStateProjection
from services.control_plane.migrations import (
    LATEST_SCHEMA_VERSION,
    MigrationError,
    current_schema_version,
    migrate_database,
    rollback_database,
)


@contextmanager
def _running_service(
    tmp_path: Path, *, hard_cap_minor: int = 100
) -> Iterator[tuple[str, subprocess.Popen[str]]]:
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
            "--evidence-root",
            str(tmp_path / "evidence"),
            "--governance-database",
            str(tmp_path / "governance.sqlite3"),
            "--hard-cap-minor",
            str(hard_cap_minor),
            "--video-root",
            str(tmp_path / "video"),
            "--product-proof-database",
            str(tmp_path / "product-proof.sqlite3"),
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


def _submit_approve_execute(
    base_url: str,
    request_id: str,
    *,
    skill_id: str,
    text: str,
) -> tuple[int, dict[str, Any]]:
    status, _ = _request(
        base_url,
        "POST",
        "/v1/governance/commands",
        payload={
            "operation": "submit",
            "request_id": request_id,
            "requester_id": "requester-1",
            "agent_id": "agent-1",
            "skill_id": skill_id,
            "capability": "render",
            "payload": {"text": text},
            "secret_ids": [],
        },
    )
    assert status == 200
    status, _ = _request(
        base_url,
        "POST",
        "/v1/governance/commands",
        payload={
            "operation": "decide",
            "request_id": request_id,
            "approver": "human-owner",
            "decision": "approved",
        },
    )
    assert status == 200
    return _request(
        base_url,
        "POST",
        "/v1/governance/commands",
        payload={"operation": "execute", "request_id": request_id},
    )


def _windows_desktop_request(
    base_url: str,
    *,
    mode: str,
    request_id: str,
    grant_id: str | None = None,
) -> dict[str, Any]:
    powershell = Path(
        "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
    )
    if not powershell.is_file():
        pytest.skip("native Windows PowerShell interop is unavailable")
    script = Path(__file__).resolve().parents[1] / (
        "apps/desktop/windows/ilaios_recovery_client.ps1"
    )
    windows_path = subprocess.run(
        ("wslpath", "-w", str(script)),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    command = [
        str(powershell),
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        windows_path,
        "-BaseUrl",
        base_url,
        "-Token",
        "runtime-secret",
        "-Mode",
        mode,
        "-RequestId",
        request_id,
    ]
    if grant_id is not None:
        command.extend(("-GrantId", grant_id))
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"Windows Desktop client failed: {completed.stdout}{completed.stderr}"
        )
    return cast(dict[str, Any], json.loads(completed.stdout.strip()))


@contextmanager
def _running_web_control(
    tmp_path: Path, *, token: str = "runtime-secret", name: str = "web"
) -> Iterator[str]:
    ready_file = tmp_path / f"{name}-ready.json"
    environment = os.environ.copy()
    environment["ILAIOS_WEB_CONTROL_TOKEN"] = token
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "apps.web.server",
            "--ready-file",
            str(ready_file),
            "--upstream-ready-file",
            str(tmp_path / "ready.json"),
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
            raise AssertionError(f"web control process exited early: {output}")
        if time.monotonic() >= deadline:
            process.kill()
            raise AssertionError("web control process did not become ready")
        time.sleep(0.01)
    ready = json.loads(ready_file.read_text(encoding="utf-8"))
    try:
        yield f"http://{ready['host']}:{ready['port']}"
    finally:
        process.terminate()
        process.wait(timeout=10)


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


def test_evidence_bytes_and_provenance_survive_real_process_restart(
    tmp_path: Path,
) -> None:
    content = b"real governed output bytes\x00\xff"
    with _running_service(tmp_path) as (base_url, first_process):
        status, stored = _request(
            base_url,
            "POST",
            "/v1/evidence/commands",
            payload={
                "operation": "store_execution_artifact",
                "execution_id": "execution-runtime-1",
                "action": "render.completed",
                "content_base64": base64.b64encode(content).decode("ascii"),
            },
        )
        assert status == 201
        digest = stored["artifact"]["digest"]
        assert stored["artifact"]["size"] == len(content)
        assert stored["provenance"]["artifact_digest"] == digest

        status, fetched = _request(
            base_url, "GET", f"/v1/evidence/artifacts/{digest}"
        )
        assert status == 200
        assert base64.b64decode(fetched["content_base64"], validate=True) == content

    (tmp_path / "ready.json").unlink()
    with _running_service(tmp_path) as (base_url, second_process):
        assert second_process.pid != first_process.pid
        status, fetched = _request(
            base_url, "GET", f"/v1/evidence/artifacts/{digest}"
        )
        assert status == 200
        assert base64.b64decode(fetched["content_base64"], validate=True) == content
        status, verified = _request(base_url, "GET", "/v1/evidence/verify")
        assert status == 200
        assert verified["records"] == [stored["provenance"]]


def test_evidence_service_rejects_artifact_tampering_after_restart(
    tmp_path: Path,
) -> None:
    with _running_service(tmp_path) as (base_url, _):
        status, stored = _request(
            base_url,
            "POST",
            "/v1/evidence/commands",
            payload={
                "operation": "store_execution_artifact",
                "execution_id": "execution-runtime-2",
                "action": "delivery.created",
                "content_base64": base64.b64encode(b"original delivery").decode(
                    "ascii"
                ),
            },
        )
        assert status == 201

    digest = stored["artifact"]["digest"]
    (tmp_path / "evidence" / "artifacts" / digest).write_bytes(b"tampered")
    (tmp_path / "ready.json").unlink()
    with _running_service(tmp_path) as (base_url, _):
        status, rejected = _request(base_url, "GET", "/v1/evidence/verify")
        assert status == 400
        assert rejected == {"error": "artifact integrity check failed"}
        status, rejected = _request(
            base_url, "GET", f"/v1/evidence/artifacts/{digest}"
        )
        assert status == 400
        assert rejected == {"error": "artifact integrity check failed"}


def test_evidence_service_rejects_provenance_tampering_after_restart(
    tmp_path: Path,
) -> None:
    with _running_service(tmp_path) as (base_url, _):
        status, _ = _request(
            base_url,
            "POST",
            "/v1/evidence/commands",
            payload={
                "operation": "store_execution_artifact",
                "execution_id": "execution-runtime-3",
                "action": "artifact.created",
                "content_base64": base64.b64encode(b"untouched bytes").decode("ascii"),
            },
        )
        assert status == 201

    with sqlite3.connect(tmp_path / "evidence" / "provenance.sqlite3") as connection:
        connection.execute("UPDATE provenance SET action = 'forged.action'")
    (tmp_path / "ready.json").unlink()
    with _running_service(tmp_path) as (base_url, _):
        status, rejected = _request(base_url, "GET", "/v1/evidence/verify")
        assert status == 400
        assert rejected == {"error": "provenance hash chain is invalid"}


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


def test_live_state_replay_reorder_gap_snapshot_and_dlp_cross_boundary(
    tmp_path: Path,
) -> None:
    with _running_service(tmp_path) as (base_url, _):
        published: list[dict[str, Any]] = []
        for event_type, state in (
            ("job.created", {"state": "pending", "token": "raw-token"}),
            ("job.started", {"state": "running"}),
            ("job.completed", {"state": "completed"}),
        ):
            status, event = _request(
                base_url,
                "POST",
                "/v1/live/events",
                payload={
                    "aggregate_id": "job-live-1",
                    "event_type": event_type,
                    "state": state,
                },
            )
            assert status == 201
            published.append(event)
        assert published[0]["state"]["token"] == "[REDACTED]"
        status, replayed = _request(
            base_url, "GET", "/v1/live/events?after_sequence=0"
        )
        assert status == 200
        assert replayed["events"] == published
        status, denied = _request(
            base_url, "GET", "/v1/live/events", token="wrong"
        )
        assert status == 401
        assert denied == {"error": "invalid local bearer token"}

    raw_database = (tmp_path / "state.sqlite3").read_bytes().decode(errors="ignore")
    assert "raw-token" not in raw_database
    events = tuple(LiveEvent(**event) for event in published)
    projection = LiveStateProjection()
    projection.reconcile(tuple(reversed(events)))
    assert projection.state("job-live-1") == {"state": "completed"}

    with pytest.raises(LiveStateError, match="gap"):
        LiveStateProjection().reconcile((events[1],))

    (tmp_path / "ready.json").unlink()
    with _running_service(tmp_path) as (base_url, _):
        _, replay_after_reconnect = _request(
            base_url,
            "GET",
            f"/v1/live/events?after_sequence={published[0]['sequence']}",
        )
        assert replay_after_reconnect["events"] == published[1:]
        _, snapshot_payload = _request(
            base_url,
            "GET",
            "/v1/live/snapshot?aggregate_id=job-live-1",
        )
        recovered = LiveStateProjection()
        recovered.restore_snapshot(LiveEvent(**snapshot_payload))
        assert recovered.last_sequence == 3
        assert recovered.state("job-live-1") == {"state": "completed"}


def test_persisted_governed_runtime_executes_real_adapter_and_rejects_tamper(
    tmp_path: Path,
) -> None:
    skill_bytes = b"immutable uppercase skill v1"
    with _running_service(tmp_path) as (base_url, _):
        registration_payloads: tuple[dict[str, object], ...] = (
            {
                "operation": "register_agent",
                "agent_id": "agent-1",
                "authorities": ["render"],
            },
            {
                "operation": "register_skill",
                "skill_id": "uppercase",
                "content_base64": base64.b64encode(skill_bytes).decode(),
                "authorities": ["render"],
            },
            {
                "operation": "register_provider",
                "provider_id": "z-local",
                "capabilities": ["render"],
                "adapter_kind": "uppercase-text",
            },
            {
                "operation": "register_provider",
                "provider_id": "a-local",
                "capabilities": ["render"],
                "adapter_kind": "uppercase-text",
            },
        )
        for payload in registration_payloads:
            status, _ = _request(
                base_url, "POST", "/v1/runtime/commands", payload=payload
            )
            assert status == 200
        status, execution = _submit_approve_execute(
            base_url,
            "runtime-request-1",
            skill_id="uppercase",
            text="real adapter output",
        )
        assert status == 200
        assert execution["provider_id"] == "a-local"
        assert execution["deterministic_first"] is True
        assert execution["output"] == {"text": "REAL ADAPTER OUTPUT"}
        status, unapproved = _submit_approve_execute(
            base_url,
            "runtime-request-2",
            skill_id="unknown",
            text="denied",
        )
        assert status == 400
        assert unapproved == {"error": "skill is not approved"}

    (tmp_path / "ready.json").unlink()
    with _running_service(tmp_path) as (base_url, _):
        status, routes = _request(base_url, "GET", "/v1/runtime/routes")
        assert status == 200
        assert len(routes["routes"]) == 1
        assert routes["routes"][0]["output"] == {"text": "REAL ADAPTER OUTPUT"}

    with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
        connection.execute(
            "UPDATE runtime_skills SET content = ? WHERE skill_id = ?",
            (b"tampered", "uppercase"),
        )
    (tmp_path / "ready.json").unlink()
    with _running_service(tmp_path) as (base_url, _):
        status, rejected = _submit_approve_execute(
            base_url,
            "runtime-request-3",
            skill_id="uppercase",
            text="must not execute",
        )
        assert status == 400
        assert rejected == {"error": "skill digest does not match approval"}
        _, routes = _request(base_url, "GET", "/v1/runtime/routes")
        assert len(routes["routes"]) == 1


def test_real_runtime_cannot_bypass_secret_dlp_hitl_or_financial_gates(
    tmp_path: Path,
) -> None:
    skill_bytes = b"governed financial uppercase skill"
    with _running_service(tmp_path, hard_cap_minor=10) as (base_url, _):
        registrations: tuple[dict[str, object], ...] = (
            {
                "operation": "register_agent",
                "agent_id": "agent-1",
                "authorities": ["render"],
            },
            {
                "operation": "register_skill",
                "skill_id": "uppercase",
                "content_base64": base64.b64encode(skill_bytes).decode("ascii"),
                "authorities": ["render"],
            },
            {
                "operation": "register_provider",
                "provider_id": "local-zero-network",
                "capabilities": ["render"],
                "adapter_kind": "uppercase-text",
            },
        )
        for registration in registrations:
            status, _ = _request(
                base_url, "POST", "/v1/runtime/commands", payload=registration
            )
            assert status == 200

        status, bypassed = _request(
            base_url,
            "POST",
            "/v1/runtime/commands",
            payload={
                "operation": "execute",
                "agent_id": "agent-1",
                "skill_id": "uppercase",
                "capability": "render",
                "payload": {"text": "bypass"},
            },
        )
        assert status == 403
        assert bypassed == {"error": "runtime execution requires governed work"}

        status, _ = _request(
            base_url,
            "POST",
            "/v1/governance/commands",
            payload={
                "operation": "register_secret_reference",
                "secret_id": "provider-key",
                "reference": "kms://tenant-a/provider-key",
            },
        )
        assert status == 200
        status, dlp_rejected = _request(
            base_url,
            "POST",
            "/v1/governance/commands",
            payload={
                "operation": "submit",
                "request_id": "dlp-rejected",
                "requester_id": "requester-1",
                "agent_id": "agent-1",
                "skill_id": "uppercase",
                "capability": "render",
                "payload": {"token": "inline-credential"},
                "secret_ids": ["provider-key"],
            },
        )
        assert status == 403
        assert dlp_rejected == {"error": "DLP rejected inline secret material"}

        status, submitted = _request(
            base_url,
            "POST",
            "/v1/governance/commands",
            payload={
                "operation": "submit",
                "request_id": "governed-request-1",
                "requester_id": "requester-1",
                "agent_id": "agent-1",
                "skill_id": "uppercase",
                "capability": "render",
                "payload": {"text": "approved runtime"},
                "secret_ids": ["provider-key"],
            },
        )
        assert status == 200
        assert submitted["risk"] == "high"
        assert submitted["quoted_minor"] == 10
        status, denied = _request(
            base_url,
            "POST",
            "/v1/governance/commands",
            payload={"operation": "execute", "request_id": "governed-request-1"},
        )
        assert status == 403
        assert denied == {"error": "high-risk work requires durable human approval"}
        status, self_approval = _request(
            base_url,
            "POST",
            "/v1/governance/commands",
            payload={
                "operation": "decide",
                "request_id": "governed-request-1",
                "approver": "requester-1",
                "decision": "approved",
            },
        )
        assert status == 403
        assert self_approval == {"error": "independent human approver is required"}
        status, _ = _request(
            base_url,
            "POST",
            "/v1/governance/commands",
            payload={
                "operation": "decide",
                "request_id": "governed-request-1",
                "approver": "human-owner",
                "decision": "approved",
            },
        )
        assert status == 200

    (tmp_path / "ready.json").unlink()
    with _running_service(tmp_path, hard_cap_minor=10) as (base_url, _):
        status, executed = _request(
            base_url,
            "POST",
            "/v1/governance/commands",
            payload={"operation": "execute", "request_id": "governed-request-1"},
        )
        assert status == 200
        assert executed["output"] == {"text": "APPROVED RUNTIME"}
        assert executed["metered_units"] == 1
        assert executed["reserved_minor"] == executed["actual_minor"] == 10

        status, _ = _request(
            base_url,
            "POST",
            "/v1/governance/commands",
            payload={
                "operation": "submit",
                "request_id": "governed-request-2",
                "requester_id": "requester-1",
                "agent_id": "agent-1",
                "skill_id": "uppercase",
                "capability": "render",
                "payload": {"text": "over cap"},
                "secret_ids": [],
            },
        )
        assert status == 200
        status, _ = _request(
            base_url,
            "POST",
            "/v1/governance/commands",
            payload={
                "operation": "decide",
                "request_id": "governed-request-2",
                "approver": "human-owner",
                "decision": "approved",
            },
        )
        assert status == 200
        status, capped = _request(
            base_url,
            "POST",
            "/v1/governance/commands",
            payload={"operation": "execute", "request_id": "governed-request-2"},
        )
        assert status == 403
        assert capped == {"error": "financial hard cap exceeded"}
        status, state = _request(base_url, "GET", "/v1/governance/state")
        assert status == 200
        assert state["ledger"] == [
            {
                "reservation_id": "governed-request-1",
                "reserved_minor": 10,
                "actual_minor": 10,
                "status": "reconciled",
            }
        ]
        assert state["secret_references"] == [
            {
                "secret_id": "provider-key",
                "reference": "kms://tenant-a/provider-key",
            }
        ]


def test_real_local_video_crosses_grant_finops_evidence_and_delivery_boundaries(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 8, 9, tzinfo=timezone.utc)
    with _running_service(tmp_path) as (base_url, _):
        status, _ = _request(
            base_url,
            "POST",
            "/v1/governance/commands",
            payload={
                "operation": "submit",
                "request_id": "video-request-1",
                "requester_id": "video-requester",
                "agent_id": "video-agent",
                "skill_id": "video-chain-v30",
                "capability": "video",
                "payload": {"objective": "deterministic local delivery"},
                "secret_ids": [],
            },
        )
        assert status == 200
        status, _ = _request(
            base_url,
            "POST",
            "/v1/governance/commands",
            payload={
                "operation": "decide",
                "request_id": "video-request-1",
                "approver": "video-owner",
                "decision": "approved",
            },
        )
        assert status == 200
        status, _ = _request(
            base_url,
            "POST",
            "/v1/grants/commands",
            payload={
                "operation": "register",
                "grant_id": "video-grant-1",
                "subject_id": "worker-video",
                "actions": ["video.execute"],
                "resources": ["video-job-1"],
                "now": now.isoformat(),
                "expires_at": (now + timedelta(minutes=5)).isoformat(),
                "max_side_effects": 1,
                "max_resources": 1,
            },
        )
        assert status == 200
        status, result = _request(
            base_url,
            "POST",
            "/v1/video/commands",
            payload={
                "operation": "execute_local",
                "request_id": "video-request-1",
                "job_id": "video-job-1",
                "grant_id": "video-grant-1",
                "now": now.isoformat(),
            },
        )
        assert status == 200
        assert result["final_stage"] == "completed"
        assert result["executed_stage_count"] == 15
        assert result["qa"]["passed"] is True
        assert result["qa"]["video_codec"] == "h264"
        assert result["qa"]["audio_codec"] == "aac"
        assert result["qa"]["width"] == 160
        assert result["qa"]["height"] == 284
        assert result["latency_passed"] is True
        assert result["latency_ms"] <= result["latency_budget_ms"]
        assert result["reserved_minor"] == result["actual_minor"] == 10
        assert result["provider_boundary"] == "local-ffmpeg"
        assert result["publisher_boundary"] == "deterministic-local-delivery"

        delivery = result["delivery"]
        delivered_path = Path(delivery["path"])
        delivered_bytes = delivered_path.read_bytes()
        assert delivered_bytes
        assert delivery["size"] == len(delivered_bytes)
        assert delivery["sha256"] == result["artifact_digest"]
        assert delivery["sha256"] == hashlib.sha256(delivered_bytes).hexdigest()
        status, artifact = _request(
            base_url,
            "GET",
            f"/v1/evidence/artifacts/{result['artifact_digest']}",
        )
        assert status == 200
        assert (
            base64.b64decode(artifact["content_base64"], validate=True)
            == delivered_bytes
        )
        status, verified = _request(base_url, "GET", "/v1/evidence/verify")
        assert status == 200
        assert verified["records"][0]["record_hash"] == result[
            "provenance_record_hash"
        ]

    (tmp_path / "ready.json").unlink()
    with _running_service(tmp_path) as (base_url, _):
        status, delivery_after_restart = _request(
            base_url,
            "GET",
            f"/v1/video/deliveries/{result['delivery']['delivery_id']}",
        )
        assert status == 200
        assert delivery_after_restart == result["delivery"]
        status, governance = _request(base_url, "GET", "/v1/governance/state")
        assert status == 200
        assert governance["ledger"] == [
            {
                "reservation_id": "video-request-1",
                "reserved_minor": 10,
                "actual_minor": 10,
                "status": "reconciled",
            }
        ]
        status, grants = _request(base_url, "GET", "/v1/grants/state")
        assert status == 200
        assert grants["grants"][0]["used_side_effects"] == 1


def test_native_windows_desktop_request_produces_durable_acceptance_manifest(
    tmp_path: Path,
) -> None:
    with _running_service(tmp_path) as (base_url, _):
        prepared = _windows_desktop_request(
            base_url, mode="Prepare", request_id="windows-proof-1"
        )
        runtime = prepared["windows_runtime"]
        preparation = prepared["response"]
        assert runtime["os_version"].startswith("Microsoft Windows NT")
        assert runtime["process_path"].lower().endswith("powershell.exe")
        assert preparation["status"] == "pending_independent_approval_and_grant"

        now = datetime.now(timezone.utc)
        status, _ = _request(
            base_url,
            "POST",
            "/v1/governance/commands",
            payload={
                "operation": "decide",
                "request_id": "windows-proof-1",
                "approver": "independent-product-owner",
                "decision": "approved",
            },
        )
        assert status == 200
        status, _ = _request(
            base_url,
            "POST",
            "/v1/grants/commands",
            payload={
                "operation": "register",
                "grant_id": "windows-proof-grant",
                "subject_id": "worker-video",
                "actions": ["video.execute"],
                "resources": [preparation["job_id"]],
                "now": now.isoformat(),
                "expires_at": (now + timedelta(minutes=5)).isoformat(),
                "max_side_effects": 1,
                "max_resources": 1,
            },
        )
        assert status == 200

        executed = _windows_desktop_request(
            base_url,
            mode="Execute",
            request_id="windows-proof-1",
            grant_id="windows-proof-grant",
        )
        assert executed["windows_runtime"]["os_version"] == runtime["os_version"]
        assert executed["windows_runtime"]["process_path"] == runtime["process_path"]
        manifest = executed["response"]
        assert manifest["accepted"] is True
        assert manifest["request_id"] == "windows-proof-1"
        assert manifest["goal_id"] == preparation["goal_id"]
        assert manifest["job_id"] == preparation["job_id"]
        assert manifest["proposal_id"] == preparation["proposal_id"]
        assert manifest["workflow_id"] == preparation["workflow_id"]
        assert manifest["worker_id"] == preparation["worker_id"]
        assert manifest["approval_proven"] is True
        assert manifest["dag_proven"] is True
        assert manifest["worker_lease_proven"] is True
        assert manifest["cost_proven"] is True
        assert manifest["job_state_proven"] is True
        assert manifest["qa"]["passed"] is True
        assert manifest["artifact_digest"] == manifest["delivery_sha256"]

        status, events = _request(base_url, "GET", "/v1/events")
        assert status == 200
        assert [event["event_type"] for event in events["events"]] == [
            "goal.created",
            "job.created",
            "proposal.created",
            "job.updated",
            "job.updated",
            "job.updated",
        ]
        status, scheduler = _request(base_url, "GET", "/v1/scheduler/state")
        assert status == 200
        assert scheduler["effects"][0]["task_id"] == preparation["job_id"]

    with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
        task_rows = connection.execute(
            "SELECT task_id, status FROM workflow_tasks ORDER BY task_id"
        ).fetchall()
        assert task_rows == [("delivery", "completed"), ("video", "completed")]

    (tmp_path / "ready.json").unlink()
    with _running_service(tmp_path) as (base_url, _):
        status, persisted = _request(
            base_url,
            "GET",
            "/v1/product-proof/manifests/windows-proof-1",
        )
        assert status == 200
        assert persisted == manifest
        status, delivery = _request(
            base_url,
            "GET",
            f"/v1/video/deliveries/{manifest['delivery_id']}",
        )
        assert status == 200
        assert delivery["sha256"] == manifest["artifact_digest"]
        status, evidence = _request(base_url, "GET", "/v1/evidence/verify")
        assert status == 200
        assert evidence["records"][0]["record_hash"] == manifest["evidence_hash"]


def test_runnable_web_control_center_has_parity_reconnect_and_no_authority(
    tmp_path: Path,
) -> None:
    with _running_web_control(tmp_path) as web_url:
        with urlopen(web_url + "/", timeout=5) as response:
            html = response.read().decode("utf-8")
        assert "ILAIOS Control Center" in html
        assert "fetch('/api/events')" in html
        assert "indexedDB" not in html
        assert "localStorage" not in html

        with _running_service(tmp_path) as (control_url, _):
            status, goal = _request(
                web_url,
                "POST",
                "/api/goals",
                payload={"objective": "Web and Desktop share authoritative state"},
            )
            assert status == 201
            status, job = _request(
                web_url,
                "POST",
                "/api/jobs",
                payload={"goal_id": goal["goal_id"]},
            )
            assert status == 201
            status, direct_goal = _request(
                control_url, "GET", f"/v1/goals/{goal['goal_id']}"
            )
            assert status == 200
            assert direct_goal == goal
            status, direct_job = _request(
                control_url, "GET", f"/v1/jobs/{job['job_id']}"
            )
            assert status == 200
            assert direct_job == job
            status, projected = _request(web_url, "GET", "/api/events")
            assert status == 200
            assert [event["event_type"] for event in projected["events"]] == [
                "goal.created",
                "job.created",
            ]

        status, unavailable = _request(web_url, "GET", "/api/events")
        assert status == 503
        assert unavailable == {"error": "control plane unavailable"}
        (tmp_path / "ready.json").unlink()
        with _running_service(tmp_path) as (_, _):
            status, reconnected = _request(web_url, "GET", "/api/events")
            assert status == 200
            assert reconnected == projected
            with _running_web_control(
                tmp_path, token="wrong-token", name="denied-web"
            ) as denied_url:
                status, denied = _request(denied_url, "GET", "/api/events")
                assert status == 401
                assert denied == {"error": "invalid local bearer token"}

    assert not (tmp_path / "web-state.sqlite3").exists()


def test_concurrent_scheduler_fences_stale_side_effects_and_survives_restart(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 8, 9, tzinfo=timezone.utc)
    with _running_service(tmp_path) as (base_url, _):
        for worker_id in ("worker-b", "worker-a"):
            status, _ = _request(
                base_url,
                "POST",
                "/v1/scheduler/commands",
                payload={
                    "operation": "register_worker",
                    "worker_id": worker_id,
                    "capabilities": ["render"],
                    "max_concurrent_tasks": 1,
                },
            )
            assert status == 200

        schedule_payload: dict[str, object] = {
            "operation": "schedule",
            "task_id": "task-race",
            "capability": "render",
            "now": now.isoformat(),
        }
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(
                pool.map(
                    lambda _: _request(
                        base_url,
                        "POST",
                        "/v1/scheduler/commands",
                        payload=schedule_payload,
                    ),
                    range(2),
                )
            )
        assert sorted(status for status, _ in results) == [200, 400]
        stale = next(payload for status, payload in results if status == 200)
        assert stale["worker_id"] == "worker-a"

        status, second = _request(
            base_url,
            "POST",
            "/v1/scheduler/commands",
            payload={
                "operation": "schedule",
                "task_id": "task-2",
                "capability": "render",
                "now": now.isoformat(),
            },
        )
        assert status == 200
        assert second["worker_id"] == "worker-b"
        status, quota = _request(
            base_url,
            "POST",
            "/v1/scheduler/commands",
            payload={
                "operation": "schedule",
                "task_id": "task-3",
                "capability": "render",
                "now": now.isoformat(),
            },
        )
        assert status == 400
        assert quota == {"error": "no worker is within capability and quota"}

        after_expiry = now + timedelta(seconds=31)
        status, replacement = _request(
            base_url,
            "POST",
            "/v1/scheduler/commands",
            payload={
                "operation": "reschedule_expired",
                "task_id": "task-race",
                "capability": "render",
                "now": after_expiry.isoformat(),
            },
        )
        assert status == 200
        assert replacement["fencing_token"] == stale["fencing_token"] + 1
        status, _ = _request(
            base_url,
            "POST",
            "/v1/grants/commands",
            payload={
                "operation": "register",
                "grant_id": "grant-race",
                "subject_id": "worker-a",
                "actions": ["write"],
                "resources": ["task-race"],
                "expires_at": (after_expiry + timedelta(minutes=5)).isoformat(),
                "max_side_effects": 1,
                "max_resources": 1,
                "now": after_expiry.isoformat(),
            },
        )
        assert status == 200
        status, denied = _request(
            base_url,
            "POST",
            "/v1/scheduler/commands",
            payload={
                "operation": "record_side_effect",
                "lease": stale,
                "grant_id": "grant-race",
                "now": after_expiry.isoformat(),
                "payload": {"effect": "must-not-happen"},
            },
        )
        assert status == 400
        assert denied == {"error": "stale or replaced fencing token"}
        status, recorded = _request(
            base_url,
            "POST",
            "/v1/scheduler/commands",
            payload={
                "operation": "record_side_effect",
                "lease": replacement,
                "grant_id": "grant-race",
                "now": after_expiry.isoformat(),
                "payload": {"effect": "bounded"},
            },
        )
        assert status == 200
        assert recorded == {"recorded": True}

    (tmp_path / "ready.json").unlink()
    with _running_service(tmp_path) as (base_url, _):
        status, state = _request(base_url, "GET", "/v1/scheduler/state")
        assert status == 200
        assert state["effects"] == [
            {
                "task_id": "task-race",
                "fencing_token": 2,
                "payload_json": '{"effect": "bounded"}',
                "created_at": after_expiry.isoformat(),
            }
        ]


def test_durable_grants_revoke_kill_and_budget_gate_real_side_effects(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 8, 9, tzinfo=timezone.utc)
    with _running_service(tmp_path) as (base_url, _):
        _request(
            base_url,
            "POST",
            "/v1/scheduler/commands",
            payload={
                "operation": "register_worker",
                "worker_id": "worker-1",
                "capabilities": ["write"],
                "max_concurrent_tasks": 3,
            },
        )
        leases: dict[str, dict[str, Any]] = {}
        for task_id in ("task-allowed", "task-revoked", "task-killed"):
            _, lease = _request(
                base_url,
                "POST",
                "/v1/scheduler/commands",
                payload={
                    "operation": "schedule",
                    "task_id": task_id,
                    "capability": "write",
                    "now": now.isoformat(),
                },
            )
            leases[task_id] = lease
            _request(
                base_url,
                "POST",
                "/v1/grants/commands",
                payload={
                    "operation": "register",
                    "grant_id": "grant-" + task_id,
                    "subject_id": "worker-1",
                    "actions": ["write"],
                    "resources": [task_id],
                    "expires_at": (now + timedelta(minutes=5)).isoformat(),
                    "max_side_effects": 1,
                    "max_resources": 1,
                    "now": now.isoformat(),
                },
            )
        status, _ = _request(
            base_url,
            "POST",
            "/v1/scheduler/commands",
            payload={
                "operation": "record_side_effect",
                "lease": leases["task-allowed"],
                "grant_id": "grant-task-allowed",
                "now": now.isoformat(),
                "payload": {"effect": "allowed"},
            },
        )
        assert status == 200
        status, exhausted = _request(
            base_url,
            "POST",
            "/v1/scheduler/commands",
            payload={
                "operation": "record_side_effect",
                "lease": leases["task-allowed"],
                "grant_id": "grant-task-allowed",
                "now": now.isoformat(),
                "payload": {"effect": "denied"},
            },
        )
        assert status == 400
        assert exhausted == {"error": "side-effect budget exhausted"}
        _request(
            base_url,
            "POST",
            "/v1/grants/commands",
            payload={
                "operation": "revoke",
                "grant_id": "grant-task-revoked",
                "now": now.isoformat(),
            },
        )
        _request(
            base_url,
            "POST",
            "/v1/grants/commands",
            payload={
                "operation": "kill",
                "grant_id": "grant-task-killed",
                "subject_id": "worker-1",
                "now": now.isoformat(),
            },
        )

    (tmp_path / "ready.json").unlink()
    with _running_service(tmp_path) as (base_url, _):
        for task_id, expected in (
            ("task-revoked", "grant is revoked"),
            ("task-killed", "subject is stopped"),
        ):
            status, denied = _request(
                base_url,
                "POST",
                "/v1/scheduler/commands",
                payload={
                    "operation": "record_side_effect",
                    "lease": leases[task_id],
                    "grant_id": "grant-" + task_id,
                    "now": now.isoformat(),
                    "payload": {"effect": "must-not-resume"},
                },
            )
            assert status == 400
            assert denied == {"error": expected}
        _, scheduler_state = _request(base_url, "GET", "/v1/scheduler/state")
        assert len(scheduler_state["effects"]) == 1

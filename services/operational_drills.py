"""Measured recovery drills against the actual provider-neutral runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from services.control_plane.migrations import (
    LATEST_SCHEMA_VERSION,
    current_schema_version,
    migrate_database,
    rollback_database,
)
from services.deployment import RuntimeBackupManager, build_oci_layout
from services.readiness import PromotionEligibility, evaluate_drill_artifact

_TOKEN = "p20-runtime-drill-token"


class DrillExecutionError(RuntimeError):
    """Raised when the actual drill runtime cannot be exercised."""


class _RuntimeProcess:
    def __init__(
        self, repository: Path, state_root: Path, ready_file: Path
    ) -> None:
        self._repository = repository
        self._state_root = state_root
        self._ready_file = ready_file
        self._process: subprocess.Popen[str] | None = None
        self.base_url = ""

    def start(self) -> None:
        if self._process is not None:
            raise DrillExecutionError("runtime is already started")
        environment = {
            **os.environ,
            "ILAIOS_CONTROL_PLANE_TOKEN": _TOKEN,
            "ILAIOS_READY_FILE": str(self._ready_file),
            "ILAIOS_STATE_ROOT": str(self._state_root),
        }
        self._process = subprocess.Popen(
            (sys.executable, "-m", "services.deployment.runtime"),
            cwd=self._repository,
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            text=True,
        )
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if self._process.poll() is not None:
                raise DrillExecutionError("runtime exited before readiness")
            if self._ready_file.is_file():
                raw: object = json.loads(self._ready_file.read_text())
                if isinstance(raw, dict) and isinstance(raw.get("port"), int):
                    self.base_url = f"http://127.0.0.1:{raw['port']}"
                    status, payload = _request(self.base_url, "/health/ready")
                    if status == 200 and payload.get("status") == "ready":
                        return
            time.sleep(0.02)
        raise DrillExecutionError("runtime readiness deadline exceeded")

    def stop(self, *, crash: bool = False) -> None:
        process = self._process
        if process is None:
            return
        if process.poll() is None:
            process.kill() if crash else process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        self._process = None


def execute_operational_drills(
    repository: Path, workspace: Path
) -> PromotionEligibility:
    """Execute all required drills and return file-backed eligibility."""
    repository = repository.resolve()
    if workspace.exists():
        raise DrillExecutionError("drill workspace must not already exist")
    workspace.mkdir(parents=True)
    state_root = workspace / "state"
    runtime = _RuntimeProcess(repository, state_root, workspace / "ready-initial.json")
    runtime.start()

    try:
        security = _security_drill(runtime.base_url)
        load = _load_drill(runtime.base_url)
        revocation = _revocation_drill(runtime.base_url)
        status, goal = _request(
            runtime.base_url,
            "/v1/goals",
            method="POST",
            payload={"objective": "Survive operational recovery drills"},
        )
        if status != 201 or not isinstance(goal.get("goal_id"), str):
            raise DrillExecutionError("failed to seed durable chaos state")
        goal_id = cast(str, goal["goal_id"])

        chaos_started = time.monotonic()
        failed_url = runtime.base_url
        runtime.stop(crash=True)
        crash_observed = _connection_refused(failed_url)
        restarted = _RuntimeProcess(
            repository, state_root, workspace / "ready-restarted.json"
        )
        restarted.start()
        status, recovered_goal = _request(
            restarted.base_url, f"/v1/goals/{goal_id}"
        )
        chaos_recovery_ms = round((time.monotonic() - chaos_started) * 1000, 3)
        chaos = {
            "passed": crash_observed and status == 200 and recovered_goal == goal,
            "measurements": {
                "crash_observed": crash_observed,
                "durable_goal_recovered": recovered_goal == goal,
                "recovery_ms": chaos_recovery_ms,
                "restart_ready_status": status,
            },
        }
        restarted.stop()

        dr_started = time.monotonic()
        backup_archive = workspace / "backup" / "runtime.zip"
        backup_manifest = RuntimeBackupManager().backup(state_root, backup_archive)
        restored_root = workspace / "restored"
        restored_manifest = RuntimeBackupManager().restore(
            backup_archive, restored_root
        )
        restored_runtime = _RuntimeProcess(
            repository, restored_root, workspace / "ready-restored.json"
        )
        restored_runtime.start()
        status, restored_goal = _request(
            restored_runtime.base_url, f"/v1/goals/{goal_id}"
        )
        restored_runtime.stop()
        dr_recovery_ms = round((time.monotonic() - dr_started) * 1000, 3)
        backup_bytes = backup_archive.read_bytes()
        dr_restore = {
            "passed": (
                backup_manifest == restored_manifest
                and status == 200
                and restored_goal == goal
            ),
            "measurements": {
                "archive_sha256": hashlib.sha256(backup_bytes).hexdigest(),
                "archive_size_bytes": len(backup_bytes),
                "manifest_file_count": len(cast(dict[object, object], backup_manifest["files"])),
                "recovery_ms": dr_recovery_ms,
                "restored_goal_equal": restored_goal == goal,
            },
        }

        supply_chain = _supply_chain_drill(repository, workspace)
        rollback = _rollback_drill(restored_root / "control.sqlite3", workspace)
    finally:
        runtime.stop()

    drills: dict[str, object] = {
        "security-red-team": security,
        "chaos-outage": chaos,
        "dr-restore": dr_restore,
        "load": load,
        "compromise-revocation": revocation,
        "supply-chain": supply_chain,
        "rollback": rollback,
    }
    artifact: dict[str, object] = {
        "artifact_version": "ILAIOS_OPERATIONAL_DRILLS_V1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "drills": drills,
        "release_state": "NOT_DEPLOYED",
        "runtime": {
            "composition_command": "python -m services.deployment.runtime",
            "provider": "local-provider-neutral",
        },
    }
    artifact_path = workspace / "operational-drills.json"
    artifact_path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return evaluate_drill_artifact(artifact_path)


def _security_drill(base_url: str) -> dict[str, object]:
    attempts: list[dict[str, object]] = []
    status, _ = _request(base_url, "/v1/goals", token=None)
    attempts.append({"attack": "missing-token", "status": status})
    status, _ = _request(base_url, "/v1/goals", token="invalid-token")
    attempts.append({"attack": "invalid-token", "status": status})
    status, _ = _request(
        base_url,
        "/v1/goals",
        method="POST",
        raw_payload=b"",
        declared_content_length=1_048_577,
    )
    attempts.append({"attack": "oversized-body", "status": status})
    status, _ = _request(
        base_url,
        "/v1/runtime/commands",
        method="POST",
        payload={"operation": "execute"},
    )
    attempts.append({"attack": "direct-runtime-execution", "status": status})
    expected = [401, 401, 400, 403]
    observed = [cast(int, attempt["status"]) for attempt in attempts]
    return {
        "passed": observed == expected,
        "measurements": {
            "attempt_count": len(attempts),
            "blocked_count": sum(
                status_code in {400, 401, 403} for status_code in observed
            ),
            "responses": attempts,
        },
    }


def _load_drill(base_url: str) -> dict[str, object]:
    request_count = 80
    started = time.monotonic()

    def invoke(request_index: int) -> tuple[int, float]:
        del request_index
        request_started = time.monotonic()
        status, response = _request(base_url, "/health/live")
        del response
        return status, (time.monotonic() - request_started) * 1000

    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(invoke, range(request_count)))
    duration = time.monotonic() - started
    latencies = sorted(latency for _, latency in results)
    success_count = sum(status == 200 for status, _ in results)
    p95_index = max(0, int(len(latencies) * 0.95) - 1)
    return {
        "passed": success_count == request_count and duration < 30,
        "measurements": {
            "concurrency": 16,
            "duration_ms": round(duration * 1000, 3),
            "p95_latency_ms": round(latencies[p95_index], 3),
            "request_count": request_count,
            "success_count": success_count,
            "throughput_requests_per_second": round(request_count / duration, 3),
        },
    }


def _revocation_drill(base_url: str) -> dict[str, object]:
    now = datetime.now(timezone.utc)
    now_text = now.isoformat()
    expires = (now + timedelta(minutes=5)).isoformat()
    _expect_status(
        base_url,
        "/v1/scheduler/commands",
        {
            "operation": "register_worker",
            "worker_id": "compromised-worker",
            "capabilities": ["write"],
            "max_concurrent_tasks": 4,
        },
        200,
    )
    leases: dict[str, dict[str, Any]] = {}
    for task_id in ("task-before-revoke", "task-after-revoke", "task-after-kill"):
        status, lease = _request(
            base_url,
            "/v1/scheduler/commands",
            method="POST",
            payload={
                "operation": "schedule",
                "task_id": task_id,
                "capability": "write",
                "now": now_text,
            },
        )
        if status != 200:
            raise DrillExecutionError(f"failed to schedule {task_id}")
        leases[task_id] = lease
    for grant_id in ("revoke-grant", "kill-grant"):
        _expect_status(
            base_url,
            "/v1/grants/commands",
            {
                "operation": "register",
                "grant_id": grant_id,
                "subject_id": "compromised-worker",
                "actions": ["write"],
                "resources": list(leases),
                "expires_at": expires,
                "max_side_effects": 3,
                "max_resources": 3,
                "now": now_text,
            },
            200,
        )
    allowed_status = _record_effect(
        base_url, leases["task-before-revoke"], "revoke-grant", now_text
    )
    _expect_status(
        base_url,
        "/v1/grants/commands",
        {
            "operation": "revoke",
            "grant_id": "revoke-grant",
            "now": now_text,
        },
        200,
    )
    revoked_status = _record_effect(
        base_url, leases["task-after-revoke"], "revoke-grant", now_text
    )
    _expect_status(
        base_url,
        "/v1/grants/commands",
        {
            "operation": "kill",
            "grant_id": "kill-grant",
            "subject_id": "compromised-worker",
            "now": now_text,
        },
        200,
    )
    killed_status = _record_effect(
        base_url, leases["task-after-kill"], "kill-grant", now_text
    )
    return {
        "passed": [allowed_status, revoked_status, killed_status] == [200, 400, 400],
        "measurements": {
            "allowed_before_revoke_status": allowed_status,
            "denied_after_kill_status": killed_status,
            "denied_after_revoke_status": revoked_status,
            "durable_grant_ids": ["revoke-grant", "kill-grant"],
        },
    }


def _supply_chain_drill(repository: Path, workspace: Path) -> dict[str, object]:
    result = build_oci_layout(repository, workspace / "oci")
    blobs = workspace / "oci" / "blobs" / "sha256"
    verified = 0
    for blob in blobs.iterdir():
        if hashlib.sha256(blob.read_bytes()).hexdigest() == blob.name:
            verified += 1
    manifest_blob = blobs / result.manifest_digest
    tampered = workspace / "tampered-manifest"
    tampered.write_bytes(manifest_blob.read_bytes() + b"tamper")
    tampered_digest = hashlib.sha256(tampered.read_bytes()).hexdigest()
    tamper_detected = tampered_digest != result.manifest_digest
    return {
        "passed": verified == 3 and tamper_detected,
        "measurements": {
            "blob_count": len(tuple(blobs.iterdir())),
            "index_sha256": result.index_digest,
            "manifest_sha256": result.manifest_digest,
            "tampered_manifest_sha256": tampered_digest,
            "tamper_detected": tamper_detected,
            "verified_blob_count": verified,
        },
    }


def _rollback_drill(database: Path, workspace: Path) -> dict[str, object]:
    before = current_schema_version(database)
    rolled_back = rollback_database(database, workspace / "rollback-backup.sqlite3")
    observed_after_rollback = current_schema_version(database)
    reapplied = migrate_database(database)
    observed_after_reapply = current_schema_version(database)
    return {
        "passed": (
            before == LATEST_SCHEMA_VERSION
            and rolled_back == LATEST_SCHEMA_VERSION - 1
            and observed_after_rollback == LATEST_SCHEMA_VERSION - 1
            and reapplied == LATEST_SCHEMA_VERSION
            and observed_after_reapply == LATEST_SCHEMA_VERSION
        ),
        "measurements": {
            "backup_created": (workspace / "rollback-backup.sqlite3").is_file(),
            "schema_before": before,
            "schema_rolled_back": observed_after_rollback,
            "schema_reapplied": observed_after_reapply,
        },
    }


def _record_effect(
    base_url: str, lease: dict[str, Any], grant_id: str, now: str
) -> int:
    status, _ = _request(
        base_url,
        "/v1/scheduler/commands",
        method="POST",
        payload={
            "operation": "record_side_effect",
            "lease": lease,
            "grant_id": grant_id,
            "now": now,
            "payload": {"drill": grant_id},
        },
    )
    return status


def _expect_status(
    base_url: str, path: str, payload: dict[str, object], expected: int
) -> None:
    status, _ = _request(base_url, path, method="POST", payload=payload)
    if status != expected:
        raise DrillExecutionError(
            f"runtime command {path} returned {status}, expected {expected}"
        )


def _connection_refused(base_url: str) -> bool:
    try:
        _request(base_url, "/health/live", timeout=1)
    except DrillExecutionError:
        return True
    return False


def _request(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, object] | None = None,
    raw_payload: bytes | None = None,
    token: str | None = _TOKEN,
    timeout: float = 10,
    declared_content_length: int | None = None,
) -> tuple[int, dict[str, Any]]:
    if payload is not None and raw_payload is not None:
        raise ValueError("only one request payload form may be supplied")
    data = raw_payload
    if payload is not None:
        data = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    if declared_content_length is not None:
        if declared_content_length < 0:
            raise ValueError("declared content length must be non-negative")
        headers["Content-Length"] = str(declared_content_length)
    request = Request(base_url + path, method=method, data=data, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw: object = json.loads(response.read())
            if not isinstance(raw, dict):
                raise DrillExecutionError("runtime response must be a JSON object")
            return response.status, cast(dict[str, Any], raw)
    except HTTPError as error:
        raw_error: object = json.loads(error.read())
        if not isinstance(raw_error, dict):
            raise DrillExecutionError("runtime error must be a JSON object") from error
        return error.code, cast(dict[str, Any], raw_error)
    except (OSError, URLError) as error:
        raise DrillExecutionError("runtime connection failed") from error


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args(argv)
    eligibility = execute_operational_drills(args.repository, args.workspace)
    print(
        json.dumps(
            {
                "artifact_path": eligibility.artifact_path,
                "completed_drills": eligibility.completed_drills,
                "eligible": eligibility.eligible,
                "evidence_hash": eligibility.evidence_hash,
                "release_state": eligibility.release_state.value,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

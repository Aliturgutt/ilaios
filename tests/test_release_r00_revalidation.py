"""Independent release-zero revalidation without deployment or product repair."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from urllib.request import urlopen

import yaml

from packages.contracts.ilaios_contracts import ReleaseState
from services.control_plane.migrations import (
    LATEST_SCHEMA_VERSION,
    current_schema_version,
    migrate_database,
    rollback_database,
)
from services.deployment import build_oci_layout
from services.readiness import REQUIRED_DRILLS, evaluate_drill_artifact

REPOSITORY = Path(__file__).resolve().parents[1]
P20_EVIDENCE = (
    REPOSITORY
    / "dev/openclaw/evidence/recovery/PLATFORM.P20.RECOVERY.v1"
)


@contextmanager
def _actual_runtime(state_root: Path, ready_file: Path) -> Iterator[str]:
    environment = {
        **os.environ,
        "ILAIOS_CONTROL_PLANE_TOKEN": "r00-independent-token",
        "ILAIOS_READY_FILE": str(ready_file),
        "ILAIOS_STATE_ROOT": str(state_root),
    }
    process = subprocess.Popen(
        (sys.executable, "-m", "services.deployment.runtime"),
        cwd=REPOSITORY,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise AssertionError("deployable runtime exited before readiness")
            if ready_file.is_file():
                ready = json.loads(ready_file.read_text())
                base_url = f"http://127.0.0.1:{ready['port']}"
                try:
                    with urlopen(base_url + "/health/ready", timeout=1) as response:
                        if response.status == 200:
                            yield base_url
                            return
                except OSError:
                    pass
            time.sleep(0.02)
        raise AssertionError("deployable runtime readiness deadline exceeded")
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)


def test_actual_oci_runtime_health_migration_and_rollback(tmp_path: Path) -> None:
    p20_artifact = json.loads((P20_EVIDENCE / "runtime_artifact.json").read_text())
    historical_index = p20_artifact["drills"]["supply-chain"]["measurements"][
        "index_sha256"
    ]
    assert len(historical_index) == 64
    int(historical_index, 16)

    result = build_oci_layout(REPOSITORY, tmp_path / "oci")
    repeated = build_oci_layout(REPOSITORY, tmp_path / "oci-repeat")

    # P20 evidence records the immutable digest produced by the original
    # validation host. The OCI layer intentionally vendors the active Python
    # runtime, stdlib and linked system libraries, so a fresh runner image may
    # produce a different historical digest. Fresh revalidation must instead
    # prove deterministic output for the current host plus full blob integrity.
    assert result.index_digest == repeated.index_digest
    assert result.manifest_digest == repeated.manifest_digest
    assert result.config_digest == repeated.config_digest
    assert result.layer_digest == repeated.layer_digest
    assert result.layer_diff_id == repeated.layer_diff_id
    assert hashlib.sha256((tmp_path / "oci/index.json").read_bytes()).hexdigest() == result.index_digest

    blobs = tmp_path / "oci/blobs/sha256"
    assert len(tuple(blobs.iterdir())) == 3
    assert all(
        hashlib.sha256(blob.read_bytes()).hexdigest() == blob.name
        for blob in blobs.iterdir()
    )

    layer = gzip.decompress((blobs / result.layer_digest).read_bytes())
    assert hashlib.sha256(layer).hexdigest() == result.layer_diff_id
    rootfs = tmp_path / "rootfs"
    rootfs.mkdir()
    with tarfile.open(fileobj=io.BytesIO(layer)) as archive:
        archive.extractall(rootfs, filter="data")
    packaged = subprocess.run(
        (
            "/usr/bin/unshare",
            "--user",
            "--map-root-user",
            "--mount",
            "/usr/sbin/chroot",
            str(rootfs),
            "/usr/bin/python3.12",
            "-c",
            "import sqlite3; import services.deployment.runtime; print('r00-oci-ok')",
        ),
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
        env={"PYTHONPATH": "/opt/ilaios"},
    )
    assert packaged.returncode == 0, packaged.stderr
    assert packaged.stdout.strip() == "r00-oci-ok"

    state_root = tmp_path / "state"
    with _actual_runtime(state_root, tmp_path / "ready.json") as base_url:
        with urlopen(base_url + "/health/live", timeout=2) as live:
            assert json.loads(live.read()) == {"status": "live"}
        with urlopen(base_url + "/health/ready", timeout=2) as ready:
            payload = json.loads(ready.read())
            assert payload["status"] == "ready"
            assert payload["schema_version"] == LATEST_SCHEMA_VERSION
            assert payload["dependencies"] == {
                "artifact_store": "ready",
                "control_database": "ready",
                "knowledge_store": "disabled",
            }

    database = state_root / "control.sqlite3"
    assert current_schema_version(database) == LATEST_SCHEMA_VERSION
    rollback_backup = tmp_path / "rollback/control.sqlite3"
    assert rollback_database(database, rollback_backup) == LATEST_SCHEMA_VERSION - 1
    assert rollback_backup.is_file()
    assert current_schema_version(database) == LATEST_SCHEMA_VERSION - 1
    assert migrate_database(database) == LATEST_SCHEMA_VERSION
    assert current_schema_version(database) == LATEST_SCHEMA_VERSION


def test_every_p20_measurement_and_evidence_identity_is_revalidated() -> None:
    artifact_path = P20_EVIDENCE / "runtime_artifact.json"
    eligibility = evaluate_drill_artifact(artifact_path)
    artifact_bytes = artifact_path.read_bytes()
    assert eligibility.evidence_hash == hashlib.sha256(artifact_bytes).hexdigest()
    assert eligibility.release_state is ReleaseState.NOT_DEPLOYED
    assert set(eligibility.completed_drills) == REQUIRED_DRILLS

    runtime_values = _key_values(P20_EVIDENCE / "runtime.log")
    assert runtime_values["artifact_sha256"] == eligibility.evidence_hash
    artifact: dict[str, Any] = json.loads(artifact_bytes)
    drills: dict[str, Any] = artifact["drills"]
    assert set(drills) == REQUIRED_DRILLS
    assert [item["status"] for item in drills["security-red-team"]["measurements"]["responses"]] == [401, 401, 400, 403]
    load = drills["load"]["measurements"]
    assert load["request_count"] == load["success_count"] == 80
    assert load["concurrency"] == 16 and load["duration_ms"] > 0
    chaos = drills["chaos-outage"]["measurements"]
    assert chaos["crash_observed"] is True
    assert chaos["durable_goal_recovered"] is True
    assert chaos["restart_ready_status"] == 200 and chaos["recovery_ms"] > 0
    recovery = drills["dr-restore"]["measurements"]
    assert recovery["restored_goal_equal"] is True
    assert recovery["archive_size_bytes"] > 0
    assert len(recovery["archive_sha256"]) == 64
    revocation = drills["compromise-revocation"]["measurements"]
    assert [
        revocation["allowed_before_revoke_status"],
        revocation["denied_after_revoke_status"],
        revocation["denied_after_kill_status"],
    ] == [200, 400, 400]
    supply = drills["supply-chain"]["measurements"]
    assert supply["verified_blob_count"] == supply["blob_count"] == 3
    assert supply["tamper_detected"] is True
    assert supply["manifest_sha256"] != supply["tampered_manifest_sha256"]
    rollback = drills["rollback"]["measurements"]
    assert rollback["backup_created"] is True
    assert [
        rollback["schema_before"],
        rollback["schema_rolled_back"],
        rollback["schema_reapplied"],
    ] == [7, 6, 7]

    p20_decision = yaml.safe_load((P20_EVIDENCE / "decision.yaml").read_text())
    p19_decision = yaml.safe_load(
        (
            REPOSITORY
            / "dev/openclaw/evidence/recovery/PLATFORM.P19.RECOVERY.v1/decision.yaml"
        ).read_text()
    )
    assert p20_decision["status"] == p19_decision["status"] == "PASS"
    assert p20_decision["release_state"] == "NOT_DEPLOYED"
    assert p20_decision["proof"]["caller_supplied_boolean_acceptance"] is False


def test_release_controls_fail_closed_and_remain_not_deployed() -> None:
    eligibility = yaml.safe_load(
        (REPOSITORY / "infra/release/promotion_eligibility.yaml").read_text()
    )
    assert eligibility["release_state"] == "NOT_DEPLOYED"
    assert eligibility["deployment_performed"] is False
    assert eligibility["feature_flags"] == {
        "default_enabled": False,
        "canary_flag_defined": True,
    }
    assert eligibility["allowlists"] == {"required": True, "default_entries": []}
    assert eligibility["rollback"]["drill_evidence"].endswith(
        "PLATFORM.P20.RECOVERY.v1/decision.yaml"
    )
    assert eligibility["operational_evidence"]["artifact_sha256"] == hashlib.sha256(
        (P20_EVIDENCE / "runtime_artifact.json").read_bytes()
    ).hexdigest()
    assert eligibility["promotion"] == {
        "eligible": True,
        "explicit_human_approval_required_for_next_state": True,
    }

    r01 = yaml.safe_load(
        (REPOSITORY / "infra/release/r01_canary_prerequisites.yaml").read_text()
    )
    assert r01["current_state"] == "NOT_DEPLOYED"
    assert r01["promotion_performed"] is False
    assert r01["explicit_human_promotion_approval"] is None
    assert r01["promotion_gate"]["automated_promotion_prohibited"] is True


def _key_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values

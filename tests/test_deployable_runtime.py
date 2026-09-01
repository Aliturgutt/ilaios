"""Deployable provider-neutral runtime recovery tests for PLATFORM.P19."""

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
from typing import Any, cast
from urllib.request import Request, urlopen

import yaml

from services.control_plane.migrations import (
    LATEST_SCHEMA_VERSION,
    current_schema_version,
)
from services.deployment import RuntimeBackupManager, build_oci_layout


@contextmanager
def _runtime(state_root: Path, ready_file: Path) -> Iterator[str]:
    environment = {
        **os.environ,
        "ILAIOS_CONTROL_PLANE_TOKEN": "deployment-secret",
        "ILAIOS_READY_FILE": str(ready_file),
        "ILAIOS_STATE_ROOT": str(state_root),
    }
    process = subprocess.Popen(
        (sys.executable, "-m", "services.deployment.runtime"),
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
            raise AssertionError(f"deployable runtime exited early: {output}")
        if time.monotonic() >= deadline:
            process.kill()
            raise AssertionError("deployable runtime did not become ready")
        time.sleep(0.01)
    ready = json.loads(ready_file.read_text())
    try:
        yield f"http://{ready['host']}:{ready['port']}"
    finally:
        process.terminate()
        process.wait(timeout=10)


def _json_request(
    base_url: str, method: str, path: str, payload: dict[str, object] | None = None
) -> tuple[int, dict[str, Any]]:
    body = None if payload is None else json.dumps(payload).encode()
    request = Request(
        base_url + path,
        data=body,
        method=method,
        headers={
            "Authorization": "Bearer deployment-secret",
            "Content-Type": "application/json",
        },
    )
    with urlopen(request, timeout=10) as response:
        return response.status, cast(dict[str, Any], json.loads(response.read()))


def test_production_process_health_backup_restore_and_configuration(
    tmp_path: Path,
) -> None:
    state = tmp_path / "state"
    with _runtime(state, tmp_path / "first-ready.json") as base_url:
        status, live = _json_request(base_url, "GET", "/health/live")
        assert (status, live) == (200, {"status": "live"})
        status, ready = _json_request(base_url, "GET", "/health/ready")
        assert status == 200
        assert ready == {
            "status": "ready",
            "schema_version": LATEST_SCHEMA_VERSION,
            "dependencies": {
                "artifact_store": "ready",
                "control_database": "ready",
                "knowledge_store": "disabled",
            },
        }
        status, goal = _json_request(
            base_url,
            "POST",
            "/v1/goals",
            {"objective": "Persist through provider-neutral backup and restore"},
        )
        assert status == 201

    archive = tmp_path / "backup" / "runtime.zip"
    manifest = RuntimeBackupManager().backup(state, archive)
    assert archive.is_file()
    manifest_files = manifest["files"]
    assert isinstance(manifest_files, dict)
    assert "control.sqlite3" in manifest_files
    restored = tmp_path / "restored"
    restored_manifest = RuntimeBackupManager().restore(archive, restored)
    assert restored_manifest == manifest
    assert current_schema_version(restored / "control.sqlite3") == LATEST_SCHEMA_VERSION

    with _runtime(restored, tmp_path / "restored-ready.json") as base_url:
        status, persisted = _json_request(
            base_url, "GET", f"/v1/goals/{goal['goal_id']}"
        )
        assert status == 200
        assert persisted == goal

    profile = yaml.safe_load(
        (Path(__file__).resolve().parents[1] / "infra/deployment/runtime-profile.yaml").read_text()
    )
    assert profile["release_state"] == "NOT_DEPLOYED"
    assert profile["deployment_performed"] is False
    assert profile["secret_references"]["control_plane_token"].startswith("env://")
    assert profile["resources"]["memory_limit_mebibytes"] == 1024


def test_engine_independent_oci_layout_contains_executable_runtime(
    tmp_path: Path,
) -> None:
    repository = Path(__file__).resolve().parents[1]
    result = build_oci_layout(repository, tmp_path / "oci")
    layout = Path(result.layout_path)
    index_bytes = (layout / "index.json").read_bytes()
    assert hashlib.sha256(index_bytes).hexdigest() == result.index_digest
    index = json.loads(index_bytes)
    manifest_descriptor = index["manifests"][0]
    assert manifest_descriptor["digest"] == f"sha256:{result.manifest_digest}"
    blobs = layout / "blobs" / "sha256"
    for blob in blobs.iterdir():
        assert hashlib.sha256(blob.read_bytes()).hexdigest() == blob.name
    manifest = json.loads((blobs / result.manifest_digest).read_bytes())
    config = json.loads((blobs / result.config_digest).read_bytes())
    assert config["config"]["Entrypoint"] == [
        "/usr/bin/python3.12",
        "-m",
        "services.deployment.runtime",
    ]
    layer = gzip.decompress((blobs / result.layer_digest).read_bytes())
    assert hashlib.sha256(layer).hexdigest() == result.layer_diff_id
    rootfs = tmp_path / "rootfs"
    rootfs.mkdir()
    with tarfile.open(fileobj=io.BytesIO(layer)) as archive:
        names = set(archive.getnames())
        assert "usr/bin/python3.12" in names
        assert "opt/ilaios/services/deployment/runtime.py" in names
        archive.extractall(rootfs, filter="data")
    executed = subprocess.run(
        (
            "unshare",
            "--user",
            "--map-root-user",
            "--mount",
            "/usr/sbin/chroot",
            str(rootfs),
            "/usr/bin/python3.12",
            "-c",
            "import sqlite3; import services.deployment.runtime; print('oci-runtime-ok')",
        ),
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
        env={"PYTHONPATH": "/opt/ilaios"},
    )
    assert executed.returncode == 0, executed.stderr
    assert executed.stdout.strip() == "oci-runtime-ok"
    assert manifest["config"]["digest"] == f"sha256:{result.config_digest}"

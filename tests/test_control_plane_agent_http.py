from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from services.agent_registry import registration_for
from services.control_plane.migrations import LATEST_SCHEMA_VERSION

AGENT_ID = "ilaios.agent.security.codesec.v1"


@contextmanager
def _running_service(tmp_path: Path) -> Iterator[str]:
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
        yield f"http://{ready['host']}:{ready['port']}"
    finally:
        process.terminate()
        process.wait(timeout=10)


def _request(
    base_url: str,
    method: str,
    path: str,
    *,
    token: str = "runtime-secret",
    payload: Mapping[str, object] | None = None,
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


def test_agent_state_requires_authentication_and_is_registry_derived(tmp_path: Path) -> None:
    with _running_service(tmp_path) as base_url:
        status, _ = _request(
            base_url,
            "GET",
            "/v1/agents/state",
            token="wrong-token",
        )
        assert status == 401

        status, state = _request(base_url, "GET", "/v1/agents/state")
        assert status == 200
        agents = state["agents"]
        assert isinstance(agents, list)
        selected = next(item for item in agents if item["agent_id"] == AGENT_ID)
        manifest = registration_for(AGENT_ID).manifest
        assert selected["alias"] == manifest.alias
        assert selected["capabilities"] == sorted(manifest.capabilities)
        assert selected["permissions"] == sorted(manifest.permissions)
        assert selected["registered"] is False
        assert selected["authority_matches_canonical"] is True


def test_agent_provision_http_is_idempotent_and_updates_state(tmp_path: Path) -> None:
    with _running_service(tmp_path) as base_url:
        payload = {"operation": "provision", "agent_id": AGENT_ID}
        status, first = _request(
            base_url,
            "POST",
            "/v1/agents/commands",
            payload=payload,
        )
        assert status == 200
        assert first == {"agent_id": AGENT_ID, "registered": True, "created": True}

        status, second = _request(
            base_url,
            "POST",
            "/v1/agents/commands",
            payload=payload,
        )
        assert status == 200
        assert second == {"agent_id": AGENT_ID, "registered": True, "created": False}

        status, state = _request(base_url, "GET", "/v1/agents/state")
        assert status == 200
        selected = next(item for item in state["agents"] if item["agent_id"] == AGENT_ID)
        assert selected["registered"] is True
        assert selected["authority_matches_canonical"] is True


def test_agent_http_rejects_authority_injection_and_unknown_identity(tmp_path: Path) -> None:
    with _running_service(tmp_path) as base_url:
        status, response = _request(
            base_url,
            "POST",
            "/v1/agents/commands",
            payload={
                "operation": "provision",
                "agent_id": AGENT_ID,
                "authorities": ["admin"],
            },
        )
        assert status == 400
        assert "server-resolved" in response["error"]

        status, response = _request(
            base_url,
            "POST",
            "/v1/agents/commands",
            payload={
                "operation": "provision",
                "agent_id": "ilaios.agent.unregistered.user-defined.v1",
            },
        )
        assert status == 400
        assert response["error"] == "unknown canonical agent identity"

        status, state = _request(base_url, "GET", "/v1/agents/state")
        assert status == 200
        assert state["registered_count"] == 0

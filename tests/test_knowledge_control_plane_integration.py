"""Real-process Control Plane integration proofs for Knowledge/RAG."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast
from urllib.error import HTTPError
from urllib.request import Request, urlopen


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
            "--knowledge-database",
            str(tmp_path / "knowledge" / "knowledge.sqlite3"),
            "--knowledge-vector-database",
            str(tmp_path / "knowledge" / "vectors.sqlite3"),
            "--knowledge-principal-id",
            "service-rag",
            "--knowledge-tenant-id",
            "tenant-a",
            "--knowledge-project-id",
            "project-a",
            "--knowledge-classifications",
            "PUBLIC,INTERNAL",
            "--knowledge-purposes",
            "build,research",
            "--knowledge-residencies",
            "eu",
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    deadline = time.monotonic() + 10
    ready: dict[str, Any] | None = None
    while ready is None:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout is not None else ""
            raise AssertionError(f"control-plane process exited early: {output}")
        if ready_file.exists():
            payload = ready_file.read_text(encoding="utf-8")
            if payload.strip():
                try:
                    decoded = json.loads(payload)
                except json.JSONDecodeError:
                    pass
                else:
                    if isinstance(decoded, dict):
                        ready = cast(dict[str, Any], decoded)
                        break
        if time.monotonic() >= deadline:
            process.kill()
            raise AssertionError("control-plane process did not become ready")
        time.sleep(0.01)
    assert ready["knowledge_enabled"] is True
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


def test_knowledge_is_live_only_through_authenticated_canonical_control_plane(
    tmp_path: Path,
) -> None:
    with _running_service(tmp_path) as base_url:
        status, health = _request(base_url, "GET", "/health/ready")
        assert status == 200
        assert health["dependencies"]["knowledge_store"] == "ready"

        status, denied = _request(
            base_url, "GET", "/v1/knowledge/state", token="wrong"
        )
        assert status == 401
        assert denied == {"error": "invalid local bearer token"}

        status, source = _request(
            base_url,
            "POST",
            "/v1/knowledge/commands",
            payload={
                "operation": "ingest_source",
                "source_id": "source-a",
                "locator": "fixture://source-a",
                "content": "canonical control plane durable knowledge",
                "trusted": True,
                "classifications": ["INTERNAL"],
                "purposes": ["build"],
                "residency": "eu",
            },
        )
        assert status == 200
        assert source["tenant_id"] == "tenant-a"
        assert source["project_id"] == "project-a"

        status, result = _request(
            base_url,
            "POST",
            "/v1/knowledge/commands",
            payload={
                "operation": "retrieve",
                "retrieval_id": "retrieval-a",
                "query": "durable knowledge",
                "purpose": "build",
                "top_k": 5,
                "candidate_limit": 10,
                "max_context_chars": 2000,
            },
        )
        assert status == 200
        assert result["tenant_id"] == "tenant-a"
        assert result["project_id"] == "project-a"
        assert result["safety_boundary"] == "UNTRUSTED_KNOWLEDGE_DATA"
        assert [unit["source_id"] for unit in result["units"]] == ["source-a"]

        status, rejected = _request(
            base_url,
            "POST",
            "/v1/knowledge/commands",
            payload={
                "operation": "retrieve",
                "tenant_id": "tenant-b",
                "project_id": "project-b",
                "retrieval_id": "smuggle-scope",
                "query": "durable knowledge",
                "purpose": "build",
                "top_k": 5,
                "candidate_limit": 10,
                "max_context_chars": 2000,
            },
        )
        assert status == 400
        assert rejected == {"error": "tenant and project scope are server-resolved"}


def test_knowledge_control_plane_state_survives_real_process_restart(tmp_path: Path) -> None:
    with _running_service(tmp_path) as base_url:
        status, _ = _request(
            base_url,
            "POST",
            "/v1/knowledge/commands",
            payload={
                "operation": "ingest_source",
                "source_id": "source-a",
                "locator": "fixture://source-a",
                "content": "restart persistent governed knowledge",
                "trusted": True,
                "classifications": ["INTERNAL"],
                "purposes": ["build"],
                "residency": "eu",
            },
        )
        assert status == 200

    (tmp_path / "ready.json").unlink()
    with _running_service(tmp_path) as base_url:
        status, state = _request(base_url, "GET", "/v1/knowledge/state")
        assert status == 200
        assert state["event_count"] == 1
        assert state["vector_index"]["row_count"] == 1
        status, result = _request(
            base_url,
            "POST",
            "/v1/knowledge/commands",
            payload={
                "operation": "retrieve",
                "retrieval_id": "after-restart",
                "query": "persistent knowledge",
                "purpose": "build",
                "top_k": 5,
                "candidate_limit": 10,
                "max_context_chars": 2000,
            },
        )
        assert status == 200
        assert [unit["source_id"] for unit in result["units"]] == ["source-a"]

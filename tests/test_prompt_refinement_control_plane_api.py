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


def test_prompt_refinement_preview_is_authenticated_and_advisory(tmp_path: Path) -> None:
    with _running_service(tmp_path) as base_url:
        before_status, before = _request(base_url, "GET", "/v1/events")
        assert before_status == 200

        unauthorized_status, _ = _request(
            base_url,
            "POST",
            "/v1/prompts/refine",
            token="wrong-token",
            payload={"prompt": "build a website", "mode": "improve"},
        )
        assert unauthorized_status == 401

        status, result = _request(
            base_url,
            "POST",
            "/v1/prompts/refine",
            payload={
                "prompt": "Build a website. Never deploy to production.",
                "mode": "structure",
            },
        )
        assert status == 200
        assert result["mode"] == "structure"
        assert result["original_prompt"] == (
            "Build a website. Never deploy to production."
        )
        assert "Never deploy to production." in result["refined_prompt"]
        evaluation = result["evaluation"]
        assert isinstance(evaluation, dict)
        assert evaluation["constraints_detected"] is True
        assert evaluation["risk_cues_preserved"] is True

        after_status, after = _request(base_url, "GET", "/v1/events")
        assert after_status == 200
        assert after == before


def test_prompt_refinement_preview_rejects_unknown_mode(tmp_path: Path) -> None:
    with _running_service(tmp_path) as base_url:
        status, result = _request(
            base_url,
            "POST",
            "/v1/prompts/refine",
            payload={"prompt": "build a website", "mode": "route-for-me"},
        )
        assert status == 400
        assert "route-for-me" in result["error"]

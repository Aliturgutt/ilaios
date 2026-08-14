"""Packaged Windows entrypoint for the local ILAIOS Desktop runtime.

The Desktop launcher supplies a fresh bearer token through the process
environment. This entrypoint composes the canonical control-plane server with a
provider-neutral human identity adapter. The identity adapter is not execution
authority and forwards authenticated intent to the canonical control plane.
"""

from __future__ import annotations

import argparse
import json
import os
import threading
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

from services.control_plane.server import main as control_plane_main
from services.desktop_identity_server import DesktopIdentityHTTPServer
from services.desktop_oidc import DesktopIdentityError, DesktopOIDCService


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--ready-file", type=Path, required=True)
    arguments = parser.parse_args(argv)

    token = os.environ.get("ILAIOS_CONTROL_PLANE_TOKEN", "").strip()
    if not token:
        parser.error("ILAIOS_CONTROL_PLANE_TOKEN is required")

    root = arguments.data_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    arguments.ready_file.parent.mkdir(parents=True, exist_ok=True)
    internal_ready = root / "control-plane-internal-ready.json"
    internal_ready.unlink(missing_ok=True)
    arguments.ready_file.unlink(missing_ok=True)

    control_args = (
        "--database",
        str(root / "control-plane.sqlite3"),
        "--host",
        "127.0.0.1",
        "--port",
        "0",
        "--ready-file",
        str(internal_ready),
        "--evidence-root",
        str(root / "evidence"),
        "--governance-database",
        str(root / "governance.sqlite3"),
        "--video-root",
        str(root / "video"),
        "--product-proof-database",
        str(root / "product-proof.sqlite3"),
    )
    control_thread = threading.Thread(
        target=control_plane_main,
        args=(control_args,),
        name="ilaios-control-plane",
        daemon=True,
    )
    control_thread.start()
    control_ready = _wait_for_control_plane(internal_ready, control_thread)
    control_host = _required_ready_text(control_ready, "host")
    control_port = _required_ready_port(control_ready, "port")

    try:
        identity = DesktopOIDCService.from_environment()
    except DesktopIdentityError as error:
        raise SystemExit(f"Desktop identity configuration rejected: {error}") from error

    identity_server = DesktopIdentityHTTPServer(
        ("127.0.0.1", 0),
        bearer_token=token,
        control_plane_base_url=f"http://{control_host}:{control_port}",
        identity=identity,
    )
    identity_host, identity_port = identity_server.server_address[:2]
    ready = {
        "host": control_host,
        "port": control_port,
        "schema_version": control_ready.get("schema_version"),
        "identity_host": identity_host,
        "identity_port": identity_port,
        "account_sign_in_configured": identity is not None,
    }
    arguments.ready_file.write_text(
        json.dumps(ready, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps({"event": "desktop_ready", **ready}, sort_keys=True), flush=True)

    def stop_identity_if_control_plane_exits() -> None:
        control_thread.join()
        identity_server.shutdown()

    watchdog = threading.Thread(
        target=stop_identity_if_control_plane_exits,
        name="ilaios-control-plane-watchdog",
        daemon=True,
    )
    watchdog.start()
    try:
        identity_server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        identity_server.server_close()
    return 0


def _wait_for_control_plane(
    ready_file: Path,
    control_thread: threading.Thread,
) -> dict[str, Any]:
    for _ in range(150):
        if ready_file.is_file():
            try:
                value = json.loads(ready_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                value = None
            if isinstance(value, dict):
                return cast(dict[str, Any], value)
        if not control_thread.is_alive():
            raise RuntimeError("canonical control plane exited before readiness")
        time.sleep(0.1)
    raise RuntimeError("canonical control plane did not become ready")


def _required_ready_text(document: dict[str, Any], name: str) -> str:
    value = document.get(name)
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"control-plane readiness {name} is invalid")
    return value


def _required_ready_port(document: dict[str, Any], name: str) -> int:
    value = document.get(name)
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 65535:
        raise RuntimeError(f"control-plane readiness {name} is invalid")
    return value


if __name__ == "__main__":
    raise SystemExit(main())

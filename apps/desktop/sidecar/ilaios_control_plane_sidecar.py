"""Packaged Windows composition root for the local ILAIOS Desktop runtime.

The Desktop launcher supplies a fresh bearer token through the process
environment. This entrypoint constructs the canonical local Control Plane once
and shares its governance, scheduler, grants, evidence and finished-product
runtime with the human identity broker and one-prompt execution coordinator.
"""

from __future__ import annotations

import argparse
import json
import os
import threading
from collections.abc import Sequence
from datetime import timedelta
from pathlib import Path

from services.control_plane.api import ControlPlane, ControlPlaneConfig
from services.control_plane.live_state import LiveStateTransport
from services.control_plane.migrations import current_schema_version
from services.control_plane.server import ControlPlaneHTTPServer
from services.control_plane.workflows import WorkflowStore, WorkflowStoreConfig
from services.desktop_identity_server import DesktopIdentityHTTPServer
from services.desktop_oidc import DesktopIdentityError, DesktopOIDCService
from services.evidence import EvidenceStore
from services.execution_coordinator import ExecutionCoordinator
from services.governance import GovernedRuntimeGateway
from services.integrations import (
    DeterministicLocalVideoRuntime,
    DurableVideoProductRuntime,
)
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--ready-file", type=Path, required=True)
    parser.add_argument("--lease-seconds", type=int, default=30)
    parser.add_argument("--hard-cap-minor", type=int, default=100)
    arguments = parser.parse_args(argv)

    token = os.environ.get("ILAIOS_CONTROL_PLANE_TOKEN", "").strip()
    if not token:
        parser.error("ILAIOS_CONTROL_PLANE_TOKEN is required")
    if arguments.lease_seconds < 1:
        parser.error("--lease-seconds must be positive")
    if arguments.hard_cap_minor < 0:
        parser.error("--hard-cap-minor must be non-negative")

    root = arguments.data_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    arguments.ready_file.parent.mkdir(parents=True, exist_ok=True)
    arguments.ready_file.unlink(missing_ok=True)

    database = root / "control-plane.sqlite3"
    control_plane = ControlPlane(ControlPlaneConfig(database, token))
    workflow_store = WorkflowStore(WorkflowStoreConfig(database))
    live_state = LiveStateTransport(database)
    governed_runtime = GovernedRuntime(database)
    scheduler = DurableWorkerScheduler(
        database,
        lease_duration=timedelta(seconds=arguments.lease_seconds),
    )
    grant_policy = DurableGrantPolicy(database)
    evidence_store = EvidenceStore(root / "evidence")
    governance = GovernedRuntimeGateway(
        root / "governance.sqlite3",
        governed_runtime,
        hard_cap_minor=arguments.hard_cap_minor,
    )
    video_runtime = DeterministicLocalVideoRuntime(
        root / "video",
        grant_policy,
        governance,
        evidence_store,
    )
    product_runtime = DurableVideoProductRuntime(
        root / "product-proof.sqlite3",
        control_plane,
        workflow_store,
        scheduler,
        grant_policy,
        governance,
        video_runtime,
    )
    coordinator = ExecutionCoordinator(
        root / "execution-coordinator.sqlite3",
        control_plane,
        governance,
        grant_policy,
        product_runtime,
    )
    control_server = ControlPlaneHTTPServer(
        ("127.0.0.1", 0),
        control_plane,
        workflow_store,
        live_state,
        governed_runtime,
        scheduler,
        grant_policy,
        evidence_store,
        governance,
        video_runtime,
        product_runtime,
    )
    control_host, control_port = control_server.server_address[:2]

    try:
        identity = DesktopOIDCService.from_environment()
    except DesktopIdentityError as error:
        control_server.server_close()
        raise SystemExit(f"Desktop identity configuration rejected: {error}") from error

    identity_server = DesktopIdentityHTTPServer(
        ("127.0.0.1", 0),
        bearer_token=token,
        identity=identity,
        coordinator=coordinator,
    )
    identity_host, identity_port = identity_server.server_address[:2]

    control_thread = threading.Thread(
        target=control_server.serve_forever,
        name="ilaios-control-plane",
        daemon=True,
    )
    control_thread.start()

    ready = {
        "host": control_host,
        "port": control_port,
        "schema_version": current_schema_version(database),
        "identity_host": identity_host,
        "identity_port": identity_port,
        "account_sign_in_configured": identity is not None,
        "governed_execution_configured": identity is not None,
    }
    arguments.ready_file.write_text(
        json.dumps(ready, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps({"event": "desktop_ready", **ready}, sort_keys=True), flush=True)

    try:
        identity_server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        identity_server.shutdown()
        identity_server.server_close()
        control_server.shutdown()
        control_server.server_close()
        control_thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

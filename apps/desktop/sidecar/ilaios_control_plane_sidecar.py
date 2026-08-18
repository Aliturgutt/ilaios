"""Packaged Windows composition root for the ILAIOS Desktop runtime."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import threading
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path

from services.control_plane.api import ControlPlane, ControlPlaneConfig
from services.control_plane.live_state import LiveStateTransport
from services.control_plane.migrations import current_schema_version
from services.control_plane.server import ControlPlaneHTTPServer
from services.control_plane.workflows import WorkflowStore, WorkflowStoreConfig
from services.desktop_execution_coordinator import DesktopExecutionCoordinator
from services.desktop_identity_server import DesktopIdentityHTTPServer
from services.desktop_oidc_windows import DesktopIdentityError, DesktopOIDCService
from services.evidence import EvidenceStore
from services.execution_adapters import register_software_runtime, register_web_runtime
from services.governance import GovernedRuntimeGateway
from services.integrations import (
    DurableVideoProductRuntime,
    RecoverableSoftwareProductRuntime,
    RecoverableWebProductRuntime,
)
from services.integrations.provider_video_runtime import UnavailableProviderVideoRuntime
from services.integrations.reference_aware_provider_video_runtime import (
    ReferenceAwareProviderBackedDesktopVideoRuntime,
)
from services.integrations.video_runtime import VideoRuntimeError
from services.reference_asset_admission import (
    MAX_UNBOUND_REFERENCE_ASSETS,
    MAX_UNBOUND_REFERENCE_BYTES,
    ReferenceAssetAdmissionStore,
)
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime
from src.video_automation.openrouter_video_provider import SEEDANCE_FREE_MODEL_ID


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
    reference_assets = ReferenceAssetAdmissionStore(
        root / "reference-assets.sqlite3",
        root / "reference-assets" / "blobs",
    )
    governance = GovernedRuntimeGateway(
        root / "governance.sqlite3",
        governed_runtime,
        hard_cap_minor=arguments.hard_cap_minor,
    )
    source_head = _source_head_sha()
    os.environ["ILAIOS_SOURCE_SHA"] = source_head

    def resolve_objective(job_id: str) -> str:
        job = control_plane.get_job(token, job_id)
        goal = control_plane.get_goal(token, job.goal_id)
        return goal.objective

    provider_api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    video_model_id = os.environ.get(
        "ILAIOS_VIDEO_MODEL_ID",
        SEEDANCE_FREE_MODEL_ID,
    ).strip()
    video_qa_model_id = os.environ.get(
        "ILAIOS_VIDEO_QA_MODEL_ID",
        "openrouter/free",
    ).strip()
    video_finished_product_configured = False
    video_provider = "unavailable"
    if provider_api_key:
        try:
            video_runtime = ReferenceAwareProviderBackedDesktopVideoRuntime(
                root / "video",
                grant_policy,
                governance,
                evidence_store,
                objective_resolver=resolve_objective,
                api_key=provider_api_key,
                model_id=video_model_id,
                qa_model_id=video_qa_model_id,
                reference_assets=reference_assets,
            )
            video_finished_product_configured = True
            video_provider = ReferenceAwareProviderBackedDesktopVideoRuntime.PROVIDER_ID
        except VideoRuntimeError as error:
            video_runtime = UnavailableProviderVideoRuntime(
                root / "video",
                grant_policy,
                governance,
                evidence_store,
                reason=f"Provider-backed Video Factory configuration rejected: {error}",
            )
    else:
        video_runtime = UnavailableProviderVideoRuntime(
            root / "video",
            grant_policy,
            governance,
            evidence_store,
            reason=(
                "Provider-backed Video Factory is unavailable because "
                "OPENROUTER_API_KEY is not configured"
            ),
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
    web_runtime = RecoverableWebProductRuntime(
        root / "web-product.sqlite3",
        control_plane,
        grant_policy,
        governance,
        root / "web",
    )
    software_runtime = RecoverableSoftwareProductRuntime(
        root / "software-product-proof.sqlite3",
        control_plane,
        workflow_store,
        scheduler,
        grant_policy,
        governance,
        evidence_store,
        root / "software",
        source_head_sha=source_head,
    )
    coordinator = DesktopExecutionCoordinator(
        root / "execution-coordinator.sqlite3",
        control_plane,
        governance,
        grant_policy,
        product_runtime,
        evidence_store,
    )
    register_web_runtime(coordinator, web_runtime)
    register_software_runtime(coordinator, software_runtime)
    coordinator.recover_stale(token=token, now=datetime.now(timezone.utc))

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
        _ensure_packaged_identity_configuration()
        identity = DesktopOIDCService.from_environment()
    except (DesktopIdentityError, RuntimeError) as error:
        control_server.server_close()
        raise SystemExit(f"Desktop identity configuration rejected: {error}") from error

    identity_server = DesktopIdentityHTTPServer(
        ("127.0.0.1", 0),
        bearer_token=token,
        identity=identity,
        coordinator=coordinator,
        reference_assets=reference_assets,
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
        "video_finished_product_configured": video_finished_product_configured,
        "video_provider": video_provider,
        "video_reference_assets_configured": True,
        "video_reference_asset_limit": 20,
        "video_reference_unbound_limit": MAX_UNBOUND_REFERENCE_ASSETS,
        "video_reference_unbound_bytes_limit": MAX_UNBOUND_REFERENCE_BYTES,
        "web_finished_product_configured": True,
        "software_finished_product_configured": True,
        "execution_recovery_configured": True,
        "source_head_sha": source_head,
    }
    arguments.ready_file.write_text(
        json.dumps(ready, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps({"event": "desktop_ready", **ready}, sort_keys=True), flush=True)

    def stop_identity_if_control_plane_exits() -> None:
        control_thread.join()
        identity_server.shutdown()

    def stop_identity_if_parent_pipe_closes() -> None:
        try:
            sys.stdin.buffer.read()
        except (OSError, ValueError):
            pass
        identity_server.shutdown()

    control_watchdog = threading.Thread(
        target=stop_identity_if_control_plane_exits,
        name="ilaios-control-plane-watchdog",
        daemon=True,
    )
    parent_watchdog = threading.Thread(
        target=stop_identity_if_parent_pipe_closes,
        name="ilaios-desktop-parent-watchdog",
        daemon=True,
    )
    control_watchdog.start()
    parent_watchdog.start()

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


def _identity_configuration_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS"))
        return base / "desktop-identity" / "oidc-providers.public.json"
    return (
        Path(__file__).resolve().parents[1]
        / "packaging"
        / "identity"
        / "oidc-providers.public.json"
    )


def _ensure_packaged_identity_configuration() -> None:
    """Load non-secret provider registration metadata when no override exists."""
    if os.environ.get("ILAIOS_DESKTOP_OIDC_PROVIDERS_JSON", "").strip():
        return
    path = _identity_configuration_path()
    if not path.is_file():
        return
    try:
        raw = path.read_text(encoding="utf-8")
        document = json.loads(raw)
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError("packaged Desktop identity metadata is unreadable") from error
    if not isinstance(document, list) or not document:
        raise RuntimeError("packaged Desktop identity metadata is invalid")
    for provider in document:
        if not isinstance(provider, dict):
            raise RuntimeError("packaged Desktop identity provider is invalid")
        if "client_secret" in provider:
            raise RuntimeError(
                "packaged Desktop identity metadata must not contain client secrets"
            )
        client_id = provider.get("client_id")
        if not isinstance(client_id, str) or not client_id.strip():
            raise RuntimeError("packaged Desktop identity client id is missing")
    os.environ["ILAIOS_DESKTOP_OIDC_PROVIDERS_JSON"] = json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
    )


def _official_brand_logo() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS"))
    else:
        base = Path(__file__).resolve().parents[3]
    logo = base / "brand" / "assets" / "03-ilaios-symbol-dark.jpg"
    if not logo.is_file():
        raise RuntimeError("official ILAIOS brand logo is missing from Desktop runtime")
    return logo


def _source_head_sha() -> str:
    if getattr(sys, "frozen", False):
        path = Path(getattr(sys, "_MEIPASS")) / "build-metadata" / "source-head.txt"
        if not path.is_file():
            raise RuntimeError("Desktop source-head provenance is missing")
        value = path.read_text(encoding="utf-8").strip()
    else:
        repository = Path(__file__).resolve().parents[3]
        completed = subprocess.run(
            ("git", "rev-parse", "HEAD"),
            cwd=repository,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if completed.returncode != 0:
            raise RuntimeError("Desktop source-head provenance is unavailable")
        value = completed.stdout.strip()
    if re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise RuntimeError("Desktop source-head provenance is malformed")
    return value


if __name__ == "__main__":
    raise SystemExit(main())

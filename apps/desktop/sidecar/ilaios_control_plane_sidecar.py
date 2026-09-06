"""Packaged Windows composition root for the ILAIOS Desktop runtime."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import re
import subprocess
import sys
import threading
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path

from services.agent_readiness_store import AgentReadinessStore
from services.company_knowledge_desktop import (
    CompanyKnowledgeDesktopIdentityHTTPServer,
    TenantCompanyKnowledgeRegistry,
)
from services.control_plane.api import ControlPlane, ControlPlaneConfig
from services.control_plane.live_state import LiveStateTransport
from services.control_plane.migrations import current_schema_version
from services.control_plane.server import ControlPlaneHTTPServer
from services.control_plane.workflows import WorkflowStore, WorkflowStoreConfig
from services.desktop_execution_coordinator import DesktopExecutionCoordinator
from services.desktop_oidc_windows import DesktopIdentityError, DesktopOIDCService
from services.evidence import EvidenceStore
from services.execution_adapters import register_software_runtime, register_web_runtime
from services.governance import GovernedRuntimeGateway
from services.integrations import (
    DurableVideoProductRuntime,
    RecoverableSoftwareProductRuntime,
    RecoverableWebProductRuntime,
)
from services.integrations.desktop_video_composition import compose_desktop_video_runtime
from services.integrations.provider_video_runtime import UnavailableProviderVideoRuntime
from services.integrations.video_runtime import VideoRuntimeError
from services.integrations.web_vercel_delivery import VercelWebDeploymentAdapter
from services.openrouter_agent_catalog import (
    OpenRouterAgentCatalogError,
    discover_free_openrouter_agent_configuration,
)
from services.p0_ai_provider_config import (
    P0AIProviderConfigError,
    load_p0_ai_provider_configuration,
)
from services.p0_runtime_composition import compose_p0_runtime
from services.reference_asset_admission import (
    MAX_UNBOUND_REFERENCE_ASSETS,
    MAX_UNBOUND_REFERENCE_BYTES,
    ReferenceAssetAdmissionStore,
)
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime
from services.runtime.security_agent_adapters import SecurityAgentRuntimeAdapters
from services.source_media import (
    MAX_SOURCE_MEDIA_BYTES,
    MAX_SOURCE_MEDIA_DURATION_SECONDS,
    SourceMediaStore,
)
from services.web_agent_execution import WEB_GOVERNED_AI_CAPABILITIES
from services.web_agent_runtime import compose_web_agent_runtime


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--ready-file", type=Path, required=True)
    parser.add_argument("--desktop-pid", type=int)
    parser.add_argument("--lease-seconds", type=int, default=30)
    parser.add_argument("--hard-cap-minor", type=int, default=100)
    arguments = parser.parse_args(argv)

    token = os.environ.get("ILAIOS_CONTROL_PLANE_TOKEN", "").strip()
    if not token:
        parser.error("ILAIOS_CONTROL_PLANE_TOKEN is required")
    if arguments.desktop_pid is not None and arguments.desktop_pid < 1:
        parser.error("--desktop-pid must be positive")
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
    openrouter_api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()

    try:
        ai_configuration = load_p0_ai_provider_configuration()
    except P0AIProviderConfigError as error:
        raise SystemExit(f"Agent AI provider configuration rejected: {error}") from error
    ai_configuration_source = "explicit" if ai_configuration is not None else "disabled"
    if ai_configuration is None and openrouter_api_key:
        try:
            ai_configuration = discover_free_openrouter_agent_configuration(
                api_key=openrouter_api_key
            )
            if ai_configuration is not None:
                ai_configuration_source = "openrouter-live-free-only"
        except OpenRouterAgentCatalogError:
            ai_configuration = None
            ai_configuration_source = "openrouter-catalog-unavailable"

    security_agent_adapters = SecurityAgentRuntimeAdapters()
    runtime_adapters = dict(security_agent_adapters.runtime_adapters())
    if ai_configuration is not None:
        for adapter_kind, adapter in ai_configuration.adapter.runtime_adapters().items():
            if adapter_kind in runtime_adapters:
                raise SystemExit("Agent runtime adapter identity collision")
            runtime_adapters[adapter_kind] = adapter

    governed_runtime = GovernedRuntime(
        database,
        external_adapters=runtime_adapters,
    )
    scheduler = DurableWorkerScheduler(
        database,
        lease_duration=timedelta(seconds=arguments.lease_seconds),
    )
    grant_policy = DurableGrantPolicy(database)
    p0_agents = compose_p0_runtime(
        governed_runtime,
        grant_policy,
        engineering_skills_root=_software_factory_skills_path(),
        ai_adapter=(ai_configuration.adapter if ai_configuration is not None else None),
        ai_provider_capabilities=(
            ai_configuration.provider_capabilities
            if ai_configuration is not None
            else None
        ),
    )
    web_ai_covered = False
    if ai_configuration is not None:
        advertised_web_capabilities = frozenset(
            capability
            for provider_capabilities in ai_configuration.provider_capabilities.values()
            for capability in provider_capabilities
        )
        web_ai_covered = WEB_GOVERNED_AI_CAPABILITIES.issubset(
            advertised_web_capabilities
        )
    web_agents = compose_web_agent_runtime(
        p0_agents.named_executor,
        _software_factory_skills_path().parents[2],
        ai_adapter=(
            ai_configuration.adapter
            if ai_configuration is not None and web_ai_covered
            else None
        ),
        ai_provider_capabilities=(
            ai_configuration.provider_capabilities
            if ai_configuration is not None and web_ai_covered
            else None
        ),
    )
    readiness_store = AgentReadinessStore(root / "agent-readiness.sqlite3")
    readiness_store.verify()

    evidence_store = EvidenceStore(root / "evidence")
    reference_assets = ReferenceAssetAdmissionStore(
        root / "reference-assets.sqlite3",
        root / "reference-assets" / "blobs",
    )
    source_media = SourceMediaStore(
        root / "source-media.sqlite3",
        root / "source-media" / "blobs",
    )
    company_knowledge = TenantCompanyKnowledgeRegistry(root / "company-knowledge")
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

    video_finished_product_configured = False
    video_provider = "unavailable"
    video_provider_mode = os.environ.get(
        "ILAIOS_VIDEO_PROVIDER_MODE", "verified-free"
    ).strip()
    video_managed_budget_usd: str | None = None
    try:
        video_composition = compose_desktop_video_runtime(
            root=root / "video",
            grants=grant_policy,
            governance=governance,
            evidence=evidence_store,
            objective_resolver=resolve_objective,
            api_key=openrouter_api_key,
            reference_assets=reference_assets,
            source_media=source_media,
            product_identity_database=root / "product-proof.sqlite3",
        )
        video_runtime = video_composition.runtime
        video_finished_product_configured = video_composition.configured
        video_provider = video_composition.provider_id
        video_provider_mode = video_composition.provider_mode
        video_managed_budget_usd = video_composition.managed_budget_usd
    except VideoRuntimeError as error:
        video_runtime = UnavailableProviderVideoRuntime(
            root / "video",
            grant_policy,
            governance,
            evidence_store,
            reason=f"Provider-backed Video Factory configuration rejected: {error}",
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
        delivery_adapter=_configured_web_delivery_adapter(),
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

    identity_server = CompanyKnowledgeDesktopIdentityHTTPServer(
        ("127.0.0.1", 0),
        bearer_token=token,
        identity=identity,
        coordinator=coordinator,
        reference_assets=reference_assets,
        source_media=source_media,
        company_knowledge=company_knowledge,
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
        "p0_target_agent_count": p0_agents.target_agent_count,
        "p0_provisioned_identity_count": p0_agents.provisioned_identity_count,
        "p0_skill_count": p0_agents.skill_count,
        "p0_security_runtime_configured": p0_agents.security_provider_count == 5,
        "p0_ai_runtime_configured": p0_agents.ai_configured,
        "p0_ai_provider_count": p0_agents.ai_provider_count,
        "p0_ai_configuration_source": ai_configuration_source,
        "web_agent_target_count": web_agents.target_agent_count,
        "web_agent_provisioned_identity_count": web_agents.provisioned_identity_count,
        "web_agent_skill_count": web_agents.skill_count,
        "web_agent_ai_runtime_configured": web_agents.ai_configured,
        "web_agent_browser_tool_required": web_agents.browser_tool_required,
        "web_agent_browser_runtime_configured": False,
        "agent_readiness_store_configured": True,
        "openrouter_secret_present": bool(openrouter_api_key),
        "video_finished_product_configured": video_finished_product_configured,
        "video_provider": video_provider,
        "video_provider_mode": video_provider_mode,
        "video_managed_budget_usd": video_managed_budget_usd,
        "video_reference_assets_configured": True,
        "video_reference_asset_limit": 20,
        "video_reference_unbound_limit": MAX_UNBOUND_REFERENCE_ASSETS,
        "video_reference_unbound_bytes_limit": MAX_UNBOUND_REFERENCE_BYTES,
        "video_source_media_configured": True,
        "video_source_media_max_bytes": MAX_SOURCE_MEDIA_BYTES,
        "video_source_media_max_duration_seconds": MAX_SOURCE_MEDIA_DURATION_SECONDS,
        "company_knowledge_upload_configured": True,
        "web_finished_product_configured": True,
        "software_finished_product_configured": True,
        "execution_recovery_configured": True,
        "source_head_sha": source_head,
    }
    arguments.ready_file.write_text(
        json.dumps(ready, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps({"event": "desktop_ready", **ready}, sort_keys=True), flush=True)

    desktop_exit_cleanup_complete = threading.Event()

    def stop_identity_if_control_plane_exits() -> None:
        control_thread.join()
        identity_server.shutdown()

    def stop_identity_if_parent_pipe_closes() -> None:
        try:
            stdin_fd = sys.stdin.fileno()
            while os.read(stdin_fd, 4096):
                pass
        except (OSError, ValueError):
            pass
        identity_server.shutdown()

    def _force_exit_if_desktop_cleanup_stalls() -> None:
        if not desktop_exit_cleanup_complete.wait(timeout=3):
            _terminate_frozen_sidecar_parent()
            os._exit(0)

    def stop_identity_if_desktop_exits() -> None:
        desktop_pid = arguments.desktop_pid
        if desktop_pid is None:
            return
        _wait_for_windows_process_exit(desktop_pid)
        # A GUI crash/forced termination cannot run DesktopRuntime.dispose().
        # Start a bounded fail-safe before graceful server shutdown so any
        # non-daemon runtime worker or PyInstaller bootloader cannot leave the
        # packaged control plane orphaned indefinitely. Normal app exit still
        # reaches the authenticated /v1/runtime/shutdown path first; this is a
        # crash/owner-loss fallback only.
        threading.Thread(
            target=_force_exit_if_desktop_cleanup_stalls,
            name="ilaios-desktop-bounded-exit",
            daemon=True,
        ).start()
        identity_server.shutdown()
        control_server.shutdown()

    control_watchdog = threading.Thread(
        target=stop_identity_if_control_plane_exits,
        name="ilaios-control-plane-watchdog",
        daemon=True,
    )
    parent_watchdog = (
        threading.Thread(
            target=stop_identity_if_parent_pipe_closes,
            name="ilaios-desktop-parent-watchdog",
            daemon=True,
        )
        if arguments.desktop_pid is None
        else None
    )
    desktop_watchdog = threading.Thread(
        target=stop_identity_if_desktop_exits,
        name="ilaios-desktop-process-watchdog",
        daemon=True,
    )
    control_watchdog.start()
    if parent_watchdog is not None:
        parent_watchdog.start()
    desktop_watchdog.start()

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
        desktop_exit_cleanup_complete.set()
    return 0


def _terminate_frozen_sidecar_parent() -> None:
    """Terminate only this frozen sidecar's matching PyInstaller parent.

    PyInstaller one-file mode keeps a bootloader parent process with the same
    executable image as the Python child. ``os._exit`` terminates only the
    child, so owner-loss cleanup must also bound that instance-specific parent.
    The executable-path equality guard prevents terminating an unrelated shell
    or another ILAIOS Desktop instance.
    """
    if os.name != "nt" or not getattr(sys, "frozen", False):
        return
    parent_pid = os.getppid()
    if parent_pid < 1 or parent_pid == os.getpid():
        return
    process_query_limited_information = 0x1000
    process_terminate = 0x0001
    kernel32 = ctypes.windll.kernel32
    kernel32.OpenProcess.restype = ctypes.c_void_p
    handle = kernel32.OpenProcess(
        process_query_limited_information | process_terminate,
        False,
        parent_pid,
    )
    if not handle:
        return
    try:
        buffer = ctypes.create_unicode_buffer(32768)
        size = ctypes.c_ulong(len(buffer))
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return
        parent_image = os.path.normcase(os.path.abspath(buffer.value))
        current_image = os.path.normcase(os.path.abspath(sys.executable))
        if parent_image != current_image:
            return
        if not kernel32.TerminateProcess(handle, 0):
            return
        # TerminateProcess is asynchronous. Confirm the matching PyInstaller
        # parent is actually signaled before the Python child exits; otherwise
        # the bootloader parent can remain observable beyond the bounded
        # Desktop owner-loss window on hosted Windows runners.
        wait_object_0 = 0x00000000
        parent_exit_timeout_ms = 2000
        wait_result = kernel32.WaitForSingleObject(
            ctypes.c_void_p(handle),
            parent_exit_timeout_ms,
        )
        if wait_result != wait_object_0:
            return
    finally:
        kernel32.CloseHandle(ctypes.c_void_p(handle))


def _wait_for_windows_process_exit(process_id: int) -> None:
    """Block until the owning Windows Desktop process exits.

    The bundled sidecar is detached from the shell that launched the GUI, so
    stdin EOF is retained only as a fallback. An explicit OS process handle
    binds crash cleanup to the actual Desktop process without coupling runtime
    lifetime to PowerShell, Explorer, or another external launcher.
    """
    if os.name != "nt":
        return
    synchronize = 0x00100000
    infinite = 0xFFFFFFFF
    kernel32 = ctypes.windll.kernel32
    kernel32.OpenProcess.restype = ctypes.c_void_p
    handle = kernel32.OpenProcess(synchronize, False, process_id)
    if not handle:
        return
    try:
        kernel32.WaitForSingleObject(ctypes.c_void_p(handle), infinite)
    finally:
        kernel32.CloseHandle(ctypes.c_void_p(handle))


def _software_factory_skills_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS"))
        path = base / "tools" / "software-factory" / "skills"
    else:
        path = (
            Path(__file__).resolve().parents[3]
            / "tools"
            / "software-factory"
            / "skills"
        )
    if not path.is_dir():
        raise RuntimeError("canonical Software Factory skill registry is missing")
    return path


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


def _configured_web_delivery_adapter() -> VercelWebDeploymentAdapter | None:
    """Return the existing Vercel boundary only when its opaque env configuration is complete."""

    required = {
        "team_id": os.environ.get("ILAIOS_VERCEL_TEAM_ID", "").strip(),
        "project_id": os.environ.get("ILAIOS_VERCEL_PROJECT_ID", "").strip(),
        "project_name": os.environ.get("ILAIOS_VERCEL_PROJECT_NAME", "").strip(),
        "production_alias": os.environ.get("ILAIOS_VERCEL_PRODUCTION_ALIAS", "").strip(),
    }
    token = os.environ.get("ILAIOS_VERCEL_TOKEN", "").strip()
    if not any(required.values()) and not token:
        return None
    if not all(required.values()) or not token:
        raise RuntimeError("ILAIOS Vercel Web delivery configuration is incomplete")
    return VercelWebDeploymentAdapter(
        team_id=required["team_id"],
        project_id=required["project_id"],
        project_name=required["project_name"],
        production_alias=required["production_alias"],
        credential_provider=lambda: os.environ.get("ILAIOS_VERCEL_TOKEN", ""),
    )


def _official_brand_logo() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS"))
    else:
        base = Path(__file__).resolve().parents[3]
    logo = base / "brand" / "assets" / "05-ilaios-app-icon.jpg"
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

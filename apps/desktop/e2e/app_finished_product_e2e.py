"""Real Windows App finished-product E2E for GitHub Actions.

The test generates a bounded Flutter task-manager app, executes the canonical
Windows Flutter lifecycle through the existing ExecutionCoordinator, and persists
content-addressed evidence. It intentionally does not sign, deploy, publish, or
contact a paid/external provider.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from services.control_plane import ControlPlane, ControlPlaneConfig
from services.control_plane.workflows import WorkflowStore, WorkflowStoreConfig
from services.evidence import EvidenceStore
from services.execution_adapters import register_app_runtime
from services.execution_coordinator import ExecutionCoordinator, ExecutionState
from services.governance import GovernedRuntimeGateway
from services.integrations import DeterministicLocalVideoRuntime, DurableVideoProductRuntime
from services.integrations.app_product_runtime import (
    DurableAppProductRuntime,
    WindowsFlutterAppExecutor,
)
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime
from services.software_factory import ExecutionPolicy, SoftwareFactoryError
from services.software_factory_runtime import RuntimeCommand, RuntimeStepResult

_ALLOWED_EXECUTABLES = frozenset({"flutter", "dart", "pwsh"})
_SAFE_ENV = (
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "SYSTEMDRIVE",
    "WINDIR",
    "TEMP",
    "TMP",
    "USERPROFILE",
    "LOCALAPPDATA",
    "APPDATA",
    "PROGRAMDATA",
    "PROGRAMFILES",
    "PROGRAMFILES(X86)",
    "PUB_CACHE",
    "FLUTTER_ROOT",
    "COMSPEC",
    "VSINSTALLDIR",
    "VCINSTALLDIR",
    "VCTOOLSINSTALLDIR",
    "VCTOOLSREDISTDIR",
    "VCTOOLSVERSION",
    "WINDOWSSDKDIR",
    "WINDOWSSDKVERSION",
    "WINDOWSSDKBINPATH",
    "WINDOWSSDKVERBINPATH",
    "UNIVERSALCRTSDKDIR",
    "UCRTVERSION",
    "INCLUDE",
    "LIB",
    "LIBPATH",
    "VISUALSTUDIOVERSION",
    "DEVENVDIR",
    "EXTENSIONSDKDIR",
    "WINDOWSLIBPATH",
    "VSCMD_ARG_HOST_ARCH",
    "VSCMD_ARG_TGT_ARCH",
    "VSCMD_VER",
    "PLATFORM",
    "PREFERREDTOOLARCHITECTURE",
)
_MAX_FAILURE_OUTPUT = 4000


class _GitHubActionsWindowsBoundary:
    """Bounded command actuator for the ephemeral GitHub-hosted Windows runner."""

    def execute(
        self,
        workspace: Path,
        command: RuntimeCommand,
        policy: ExecutionPolicy,
    ) -> RuntimeStepResult:
        root = workspace.resolve()
        working = (root / command.working_directory).resolve()
        if root != working and root not in working.parents:
            raise SoftwareFactoryError("command working directory escaped app workspace")
        if not working.is_dir():
            raise SoftwareFactoryError("command working directory is unavailable")
        if not command.argv or command.argv[0].casefold() not in _ALLOWED_EXECUTABLES:
            raise SoftwareFactoryError("app Windows boundary rejected executable")
        if not policy.secure_mode or policy.network_allowed or policy.secrets_allowed:
            raise SoftwareFactoryError("app Windows boundary requires secure local-only policy")
        env = {
            key: value
            for key in _SAFE_ENV
            if (value := os.environ.get(key)) is not None
        }
        env["CI"] = "true"
        resolved = shutil.which(command.argv[0], path=env.get("PATH"))
        if resolved is None:
            raise SoftwareFactoryError(
                f"app Windows boundary could not resolve {command.argv[0]}"
            )
        invocation: tuple[str, ...]
        if Path(resolved).suffix.casefold() in {".bat", ".cmd"}:
            comspec = os.environ.get("COMSPEC", "").strip() or shutil.which("cmd.exe")
            if not comspec:
                raise SoftwareFactoryError(
                    "app Windows boundary could not resolve command interpreter"
                )
            invocation = (
                comspec,
                "/d",
                "/s",
                "/c",
                subprocess.list2cmdline((resolved, *command.argv[1:])),
            )
        else:
            invocation = (resolved, *command.argv[1:])
        process = subprocess.run(
            invocation,
            cwd=working,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=policy.timeout_seconds,
            check=False,
        )
        passed = process.returncode == 0
        print(
            "ILAIOS_APP_E2E_COMMAND "
            f"stage={command.stage} executable={command.argv[0]} "
            f"returncode={process.returncode} passed={str(passed).lower()}"
        )
        if not passed:
            stdout_tail = process.stdout.decode("utf-8", errors="replace")[-_MAX_FAILURE_OUTPUT:]
            stderr_tail = process.stderr.decode("utf-8", errors="replace")[-_MAX_FAILURE_OUTPUT:]
            if stdout_tail:
                print("ILAIOS_APP_E2E_STDOUT_TAIL_BEGIN")
                print(stdout_tail)
                print("ILAIOS_APP_E2E_STDOUT_TAIL_END")
            if stderr_tail:
                print("ILAIOS_APP_E2E_STDERR_TAIL_BEGIN")
                print(stderr_tail)
                print("ILAIOS_APP_E2E_STDERR_TAIL_END")
        return RuntimeStepResult(
            command.stage,
            command.argv,
            process.returncode,
            hashlib.sha256(process.stdout).hexdigest(),
            hashlib.sha256(process.stderr).hexdigest(),
            passed,
        )


def main() -> None:
    source_sha = os.environ.get("ILAIOS_APP_E2E_SOURCE_SHA", "").strip()
    if len(source_sha) != 40 or any(
        character not in "0123456789abcdef" for character in source_sha
    ):
        raise SystemExit("ILAIOS_APP_E2E_SOURCE_SHA must be an exact lowercase SHA-1")
    artifact_root = Path(
        os.environ.get(
            "ILAIOS_APP_E2E_ARTIFACT_DIR",
            "artifacts/app-windows-finished-product",
        )
    ).resolve()
    artifact_root.mkdir(parents=True, exist_ok=True)
    state_root = artifact_root / "state"
    state_root.mkdir(parents=True, exist_ok=True)
    state = state_root / "platform.sqlite3"

    control = ControlPlane(ControlPlaneConfig(state, "token"))
    workflows = WorkflowStore(WorkflowStoreConfig(state))
    scheduler = DurableWorkerScheduler(state, lease_duration=timedelta(seconds=30))
    grants = DurableGrantPolicy(state)
    governance = GovernedRuntimeGateway(
        state_root / "governance.sqlite3",
        GovernedRuntime(state),
        hard_cap_minor=100,
    )
    evidence = EvidenceStore(artifact_root / "coordinator-evidence")
    video = DeterministicLocalVideoRuntime(
        artifact_root / "video-unused",
        grants,
        governance,
        evidence,
    )
    video_product = DurableVideoProductRuntime(
        state_root / "video-product.sqlite3",
        control,
        workflows,
        scheduler,
        grants,
        governance,
        video,
    )
    coordinator = ExecutionCoordinator(
        state_root / "coordinator.sqlite3",
        control,
        governance,
        grants,
        video_product,
        evidence,
    )
    executor = WindowsFlutterAppExecutor(
        artifact_root / "products",
        _GitHubActionsWindowsBoundary(),
    )
    runtime = DurableAppProductRuntime(
        state_root / "app-product.sqlite3",
        control,
        grants,
        governance,
        artifact_root / "products",
        executor,
        source_head_sha=source_sha,
    )
    register_app_runtime(coordinator, runtime)

    now = datetime.now(timezone.utc)
    request_id = "app-windows-e2e"
    principal_id = "oidc|github-actions-app-e2e"
    tenant_id = "tenant/app-e2e"
    objective = "Build a Windows desktop app task manager for a product launch team"
    prepared = coordinator.prepare(
        request_id,
        objective,
        token="token",
        principal_id=principal_id,
        tenant_id=tenant_id,
        now=now,
    )
    if prepared.get("execution_status") != ExecutionState.ADMITTED.value:
        raise SystemExit(f"App E2E was not admitted: {prepared}")
    manifest = coordinator.resume(
        request_id,
        token="token",
        now=now + timedelta(seconds=1),
        principal_id=principal_id,
        tenant_id=tenant_id,
    )
    required = (
        manifest.get("accepted") is True,
        manifest.get("adapter_id") == "app.product-runtime.windows.v1",
        manifest.get("platform") == "windows",
        manifest.get("verification_scope")
        == "BOUNDED_LOCAL_TASK_CHECKLIST_WINDOWS_APP",
        manifest.get("source_head_sha") == source_sha,
        manifest.get("deployment_state") == "NOT_DEPLOYED",
        manifest.get("signed") is False,
        manifest.get("store_submitted") is False,
        manifest.get("commercial_release_pass") is False,
        int(manifest.get("artifact_size", 0)) > 0,
        len(str(manifest.get("artifact_sha256", ""))) == 64,
    )
    if not all(required):
        raise SystemExit(
            "App E2E AcceptanceManifest is incomplete or overclaims release state"
        )

    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    envelope = {
        "schema": "ilaios.app-windows-finished-product-e2e.v1",
        "source_sha": source_sha,
        "request_id": request_id,
        "manifest_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "manifest": manifest,
        "production_claim": False,
        "signing_claim": False,
        "store_claim": False,
    }
    output = artifact_root / "app_windows_finished_product_evidence.json"
    output.write_text(
        json.dumps(envelope, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("ILAIOS_APP_WINDOWS_FINISHED_PRODUCT_E2E=PASS")
    print(f"ILAIOS_APP_E2E_SOURCE_SHA={source_sha}")
    print(f"ILAIOS_APP_E2E_MANIFEST_SHA256={envelope['manifest_sha256']}")


if __name__ == "__main__":
    main()

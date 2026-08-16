"""Bounded App Factory Windows finished-product and Coordinator evidence."""

from __future__ import annotations

import hashlib
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import services.execution_coordinator as coordinator_module
from services.control_plane import ControlPlane, ControlPlaneConfig
from services.control_plane.workflows import WorkflowStore, WorkflowStoreConfig
from services.evidence import EvidenceStore
from services.execution_adapters import register_app_runtime
from services.execution_coordinator import (
    CapabilityMaturity,
    ExecutionCoordinator,
    ExecutionCoordinatorError,
    ExecutionState,
)
from services.governance import GovernedRuntimeGateway
from services.integrations import DeterministicLocalVideoRuntime, DurableVideoProductRuntime
from services.integrations.app_product_runtime import (
    AppProductRuntimeError,
    DurableAppProductRuntime,
    WindowsFlutterAppExecutor,
)
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime
from services.software_factory import ExecutionPolicy
from services.software_factory_runtime import RuntimeCommand, RuntimeStepResult

_APP = "ilaios.capability.app-factory"
_SOURCE_SHA = "1" * 40


class _FakeWindowsBoundary:
    """Test-only secure-boundary double that emits deterministic build artifacts."""

    def __init__(self) -> None:
        self.commands: list[RuntimeCommand] = []

    def execute(
        self,
        workspace: Path,
        command: RuntimeCommand,
        policy: ExecutionPolicy,
    ) -> RuntimeStepResult:
        assert workspace.is_absolute()
        assert policy.secure_mode is True
        assert policy.network_allowed is False
        assert policy.secrets_allowed is False
        self.commands.append(command)
        if command.stage == "build":
            executable = (
                workspace
                / command.working_directory
                / "build"
                / "windows"
                / "x64"
                / "runner"
                / "Release"
                / "ilaios_generated_app.exe"
            )
            executable.parent.mkdir(parents=True, exist_ok=True)
            executable.write_bytes(b"MZ-ILAIOS-TEST-EXECUTABLE")
        if command.stage == "package":
            package = (
                workspace
                / command.working_directory
                / "build"
                / "ilaios_generated_app_windows.zip"
            )
            package.parent.mkdir(parents=True, exist_ok=True)
            package.write_bytes(b"PK-ILAIOS-TEST-PACKAGE")
        stdout = hashlib.sha256(f"stdout:{command.stage}".encode()).hexdigest()
        stderr = hashlib.sha256(f"stderr:{command.stage}".encode()).hexdigest()
        return RuntimeStepResult(
            command.stage,
            command.argv,
            0,
            stdout,
            stderr,
            True,
        )


def _allow_fake_flutter_detection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep unit tests hermetic while real Windows E2E still proves Flutter exists."""
    original_which = shutil.which

    def _which(executable: str) -> str | None:
        if executable == "flutter":
            return "C:/test-only/flutter.exe"
        return original_which(executable)

    monkeypatch.setattr(shutil, "which", _which)


def _stack(
    tmp_path: Path,
) -> tuple[ExecutionCoordinator, DurableAppProductRuntime, _FakeWindowsBoundary]:
    state = tmp_path / "state.sqlite3"
    control = ControlPlane(ControlPlaneConfig(state, "token"))
    workflows = WorkflowStore(WorkflowStoreConfig(state))
    scheduler = DurableWorkerScheduler(state, lease_duration=timedelta(seconds=30))
    grants = DurableGrantPolicy(state)
    governance = GovernedRuntimeGateway(
        tmp_path / "governance.sqlite3",
        GovernedRuntime(state),
        hard_cap_minor=100,
    )
    evidence = EvidenceStore(tmp_path / "evidence")
    video = DeterministicLocalVideoRuntime(
        tmp_path / "video",
        grants,
        governance,
        evidence,
    )
    video_product = DurableVideoProductRuntime(
        tmp_path / "video-product.sqlite3",
        control,
        workflows,
        scheduler,
        grants,
        governance,
        video,
    )
    coordinator = ExecutionCoordinator(
        tmp_path / "coordinator.sqlite3",
        control,
        governance,
        grants,
        video_product,
        evidence,
    )
    boundary = _FakeWindowsBoundary()
    executor = WindowsFlutterAppExecutor(tmp_path / "app-artifacts", boundary)
    runtime = DurableAppProductRuntime(
        tmp_path / "app-product.sqlite3",
        control,
        grants,
        governance,
        tmp_path / "app-artifacts",
        executor,
        source_head_sha=_SOURCE_SHA,
    )
    return coordinator, runtime, boundary


def _install_app_runtime(
    monkeypatch: pytest.MonkeyPatch,
    coordinator: ExecutionCoordinator,
    runtime: DurableAppProductRuntime,
) -> None:
    original = coordinator_module._ADAPTER_DESCRIPTORS[_APP]
    monkeypatch.setitem(coordinator_module._ADAPTER_DESCRIPTORS, _APP, original)
    register_app_runtime(coordinator, runtime)


def test_windows_task_app_accepts_real_artifact_evidence_through_coordinator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _allow_fake_flutter_detection(monkeypatch)
    coordinator, runtime, boundary = _stack(tmp_path)
    _install_app_runtime(monkeypatch, coordinator, runtime)
    now = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
    objective = "Build a Windows desktop app task manager for a launch team"

    prepared = coordinator.prepare(
        "app-windows-1",
        objective,
        token="token",
        principal_id="oidc|app@example.test",
        tenant_id="tenant/app",
        now=now,
    )
    assert prepared["execution_status"] == ExecutionState.ADMITTED.value
    assert prepared["capability_id"] == _APP
    assert prepared["adapter_id"] == "app.product-runtime.windows.v1"

    manifest = coordinator.resume(
        "app-windows-1",
        token="token",
        now=now + timedelta(seconds=1),
        principal_id="oidc|app@example.test",
        tenant_id="tenant/app",
    )
    assert manifest["accepted"] is True
    assert manifest["adapter_id"] == "app.product-runtime.windows.v1"
    assert manifest["platform"] == "windows"
    assert manifest["verification_scope"] == "BOUNDED_LOCAL_TASK_CHECKLIST_WINDOWS_APP"
    assert manifest["source_head_sha"] == _SOURCE_SHA
    assert manifest["deployment_state"] == "NOT_DEPLOYED"
    assert manifest["signed"] is False
    assert manifest["store_submitted"] is False
    assert manifest["commercial_release_pass"] is False
    assert len(str(manifest["artifact_sha256"])) == 64
    artifact_size = manifest["artifact_size"]
    assert isinstance(artifact_size, int)
    assert artifact_size > 0
    assert [command.stage for command in boundary.commands] == [
        "scaffold",
        "prepare",
        "resolve_dependencies",
        "lint",
        "typecheck",
        "test",
        "build",
        "package",
        "smoke_test",
    ]
    assert (
        tmp_path
        / "app-artifacts"
        / "app-windows-1"
        / "project"
        / "lib"
        / "main.dart"
    ).is_file()
    assert not (tmp_path / "apps").exists()


def test_app_runtime_is_bounded_and_does_not_promote_arbitrary_apps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator, runtime, _ = _stack(tmp_path)
    _install_app_runtime(monkeypatch, coordinator, runtime)
    now = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)

    with pytest.raises(ExecutionCoordinatorError, match="outside the verified Windows"):
        coordinator.prepare(
            "app-arbitrary-1",
            "Build an iOS banking mobile app with payments",
            token="token",
            principal_id="oidc|app@example.test",
            tenant_id="tenant/app",
            now=now,
        )

    assert runtime.supports("Build a Windows desktop app task manager") is True
    assert runtime.supports("Build an Android app task manager") is False
    assert runtime.supports("Build a Windows desktop 3D game") is False


def test_default_app_descriptor_remains_review_only_without_runtime_injection() -> None:
    descriptor = coordinator_module._ADAPTER_DESCRIPTORS[_APP]
    assert descriptor.capability_id == _APP
    assert descriptor.maturity is CapabilityMaturity.REVIEW_ONLY
    assert descriptor.adapter_id is None
    assert descriptor.blocker_code == "APP_FACTORY_REVIEW_ONLY"


def test_executor_rejects_duplicate_or_unbounded_workspace_requests(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _allow_fake_flutter_detection(monkeypatch)
    boundary = _FakeWindowsBoundary()
    executor = WindowsFlutterAppExecutor(tmp_path / "app-artifacts", boundary)
    evidence = executor.build(
        "bounded-app",
        "Build a Windows desktop app task manager",
    )
    assert evidence.passed is True
    with pytest.raises(AppProductRuntimeError, match="already exists"):
        executor.build(
            "bounded-app",
            "Build a Windows desktop app task manager",
        )
    with pytest.raises(AppProductRuntimeError, match="outside the verified"):
        executor.build(
            "unbounded-app",
            "Build a Windows desktop cryptocurrency exchange",
        )

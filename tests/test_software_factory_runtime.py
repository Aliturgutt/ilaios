# mypy: disable-error-code=misc
"""SF-6 runtime adapters execute only through the governed command boundary."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from services.software_factory import ExecutionPolicy, SoftwareFactoryError
from services.software_factory_runtime import (
    FlutterRuntimeAdapter,
    NodeRuntimeAdapter,
    PythonRuntimeAdapter,
    RuntimeCommand,
    RuntimeStepResult,
    UnavailableSecureBoundary,
    evidence_json,
)


class _Boundary:
    def __init__(self) -> None:
        self.commands: list[RuntimeCommand] = []
        self.policies: list[ExecutionPolicy] = []

    def execute(
        self, workspace: Path, command: RuntimeCommand, policy: ExecutionPolicy
    ) -> RuntimeStepResult:
        assert workspace.is_absolute()
        self.commands.append(command)
        self.policies.append(policy)
        return RuntimeStepResult(
            command.stage,
            command.argv,
            0,
            hashlib.sha256(command.stage.encode()).hexdigest(),
            hashlib.sha256(b"").hexdigest(),
            True,
        )


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / "apps/website").mkdir(parents=True)
    (tmp_path / "apps/desktop").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    (tmp_path / "apps/website/package.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "apps/desktop/pubspec.yaml").write_text("name: fixture\n", encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize(
    ("adapter_type", "expected_root", "expected_commands"),
    [
        (PythonRuntimeAdapter, ".", ("python", "-m", "pytest", "-q")),
        (NodeRuntimeAdapter, "apps/website", ("pnpm", "run", "test:site")),
        (FlutterRuntimeAdapter, "apps/desktop", ("flutter", "test")),
    ],
)
def test_actual_stack_adapters_emit_complete_governed_lifecycle(
    tmp_path: Path,
    adapter_type: type[PythonRuntimeAdapter | NodeRuntimeAdapter | FlutterRuntimeAdapter],
    expected_root: str,
    expected_commands: tuple[str, ...],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _workspace(tmp_path)
    monkeypatch.setattr("services.software_factory_runtime.shutil.which", lambda _: "runtime")
    boundary = _Boundary()
    adapter = adapter_type(boundary)
    policy = ExecutionPolicy(frozenset({"src", "services", "tests", "apps"}))
    detection = adapter.detect(workspace)
    assert detection.detected and detection.executable == "runtime"

    results = (
        adapter.prepare(workspace, policy),
        adapter.resolve_dependencies(workspace, policy),
        adapter.lint(workspace, policy),
        adapter.typecheck(workspace, policy),
        adapter.test(workspace, policy),
        adapter.build(workspace, policy),
        adapter.package(workspace, policy),
        adapter.smoke_test(workspace, policy),
    )
    assert [item.stage for item in results] == [
        "prepare", "resolve_dependencies", "lint", "typecheck", "test", "build", "package", "smoke_test"
    ]
    assert all(item.working_directory == expected_root for item in boundary.commands)
    assert expected_commands in [item.argv for item in boundary.commands]
    assert boundary.policies == [policy] * 8
    evidence = adapter.collect_evidence(workspace, results)
    assert evidence.passed and len(evidence.workspace_sha256) == 64
    assert '"passed":true' in evidence_json(evidence)


def test_node_dependency_resolution_disables_package_install_hooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _workspace(tmp_path)
    monkeypatch.setattr("services.software_factory_runtime.shutil.which", lambda _: "runtime")
    boundary = _Boundary()
    adapter = NodeRuntimeAdapter(boundary)

    result = adapter.resolve_dependencies(
        workspace,
        ExecutionPolicy(frozenset({"apps"})),
    )

    assert result.passed
    assert boundary.commands == [
        RuntimeCommand(
            "resolve_dependencies",
            (
                "pnpm",
                "install",
                "--offline",
                "--frozen-lockfile",
                "--ignore-scripts",
            ),
            "apps/website",
        )
    ]


def test_missing_runtime_and_incomplete_evidence_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _workspace(tmp_path)
    monkeypatch.setattr("services.software_factory_runtime.shutil.which", lambda _: None)
    adapter = PythonRuntimeAdapter(_Boundary())
    assert not adapter.detect(workspace).detected
    with pytest.raises(SoftwareFactoryError, match="runtime is unavailable"):
        adapter.prepare(workspace, ExecutionPolicy(frozenset({"src"})))
    with pytest.raises(SoftwareFactoryError, match="incomplete"):
        adapter.collect_evidence(workspace, ())


def test_default_boundary_never_falls_back_to_unsandboxed_execution(tmp_path: Path) -> None:
    with pytest.raises(SoftwareFactoryError, match="sandbox is unavailable"):
        UnavailableSecureBoundary().execute(
            tmp_path.resolve(), RuntimeCommand("test", ("python", "-m", "pytest"), "."),
            ExecutionPolicy(frozenset({"tests"})),
        )


def test_runtime_evidence_rejects_secret_bearing_workspace(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    (workspace / ".env").write_text("TOKEN=secret\n", encoding="utf-8")
    boundary = _Boundary()
    adapter = PythonRuntimeAdapter(boundary)
    stages = (
        "prepare", "resolve_dependencies", "lint", "typecheck", "test", "build", "package", "smoke_test"
    )
    results = tuple(
        RuntimeStepResult(stage, ("safe",), 0, "0" * 64, "0" * 64, True)
        for stage in stages
    )
    with pytest.raises(SoftwareFactoryError, match="secret-bearing"):
        adapter.collect_evidence(workspace, results)

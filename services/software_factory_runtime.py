"""Governed runtime adapters for the canonical ILAIOS Software Factory."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from services.software_factory import ExecutionPolicy, SoftwareFactoryError


@dataclass(frozen=True, slots=True)
class RuntimeDetection:
    adapter_id: str
    detected: bool
    manifest: str | None
    executable: str | None
    reason: str


@dataclass(frozen=True, slots=True)
class RuntimeCommand:
    stage: str
    argv: tuple[str, ...]
    working_directory: str


@dataclass(frozen=True, slots=True)
class RuntimeStepResult:
    stage: str
    command: tuple[str, ...]
    exit_code: int
    stdout_sha256: str
    stderr_sha256: str
    passed: bool


@dataclass(frozen=True, slots=True)
class RuntimeEvidence:
    adapter_id: str
    workspace_sha256: str
    steps: tuple[RuntimeStepResult, ...]
    passed: bool


class SecureCommandBoundary(Protocol):
    """Mandatory sandbox boundary; adapters never spawn commands directly."""

    def execute(
        self,
        workspace: Path,
        command: RuntimeCommand,
        policy: ExecutionPolicy,
    ) -> RuntimeStepResult: ...


class UnavailableSecureBoundary:
    """Fail-closed boundary used until a host supplies enforceable isolation."""

    def execute(
        self,
        workspace: Path,
        command: RuntimeCommand,
        policy: ExecutionPolicy,
    ) -> RuntimeStepResult:
        del workspace, command, policy
        raise SoftwareFactoryError("secure runtime sandbox is unavailable")


class RuntimeAdapter(Protocol):
    adapter_id: str

    def detect(self, workspace: Path) -> RuntimeDetection: ...
    def prepare(self, workspace: Path, policy: ExecutionPolicy) -> RuntimeStepResult: ...
    def resolve_dependencies(self, workspace: Path, policy: ExecutionPolicy) -> RuntimeStepResult: ...
    def lint(self, workspace: Path, policy: ExecutionPolicy) -> RuntimeStepResult: ...
    def typecheck(self, workspace: Path, policy: ExecutionPolicy) -> RuntimeStepResult: ...
    def test(self, workspace: Path, policy: ExecutionPolicy) -> RuntimeStepResult: ...
    def build(self, workspace: Path, policy: ExecutionPolicy) -> RuntimeStepResult: ...
    def package(self, workspace: Path, policy: ExecutionPolicy) -> RuntimeStepResult: ...
    def smoke_test(self, workspace: Path, policy: ExecutionPolicy) -> RuntimeStepResult: ...
    def collect_evidence(
        self, workspace: Path, results: tuple[RuntimeStepResult, ...]
    ) -> RuntimeEvidence: ...


class _CommandRuntimeAdapter:
    adapter_id = "abstract"
    manifest_name = ""
    executable_name = ""
    root_hint = "."

    def __init__(
        self,
        boundary: SecureCommandBoundary,
        *,
        root_hint: str | None = None,
    ) -> None:
        self._boundary = boundary
        if root_hint is not None:
            normalized = root_hint.strip().replace("\\", "/")
            if (
                not normalized
                or normalized.startswith("/")
                or ".." in normalized.split("/")
            ):
                raise ValueError("runtime root_hint must be a bounded relative path")
            self.root_hint = normalized

    def detect(self, workspace: Path) -> RuntimeDetection:
        root = self._runtime_root(workspace)
        manifest = root / self.manifest_name
        executable = shutil.which(self.executable_name)
        detected = manifest.is_file() and executable is not None
        reason = "runtime and manifest detected" if detected else (
            "manifest missing" if not manifest.is_file() else "runtime executable missing"
        )
        return RuntimeDetection(
            self.adapter_id,
            detected,
            manifest.relative_to(workspace).as_posix() if manifest.is_file() else None,
            executable,
            reason,
        )

    def prepare(self, workspace: Path, policy: ExecutionPolicy) -> RuntimeStepResult:
        detection = self.detect(workspace)
        if not detection.detected:
            raise SoftwareFactoryError(f"{self.adapter_id} runtime is unavailable: {detection.reason}")
        return self._run(
            workspace,
            policy,
            RuntimeCommand("prepare", self._prepare_command(), self.root_hint),
        )

    def resolve_dependencies(self, workspace: Path, policy: ExecutionPolicy) -> RuntimeStepResult:
        return self._run(
            workspace,
            policy,
            RuntimeCommand("resolve_dependencies", self._dependency_command(), self.root_hint),
        )

    def lint(self, workspace: Path, policy: ExecutionPolicy) -> RuntimeStepResult:
        return self._run(
            workspace,
            policy,
            RuntimeCommand("lint", self._lint_command(), self.root_hint),
        )

    def typecheck(self, workspace: Path, policy: ExecutionPolicy) -> RuntimeStepResult:
        return self._run(
            workspace,
            policy,
            RuntimeCommand("typecheck", self._typecheck_command(), self.root_hint),
        )

    def test(self, workspace: Path, policy: ExecutionPolicy) -> RuntimeStepResult:
        return self._run(
            workspace,
            policy,
            RuntimeCommand("test", self._test_command(), self.root_hint),
        )

    def build(self, workspace: Path, policy: ExecutionPolicy) -> RuntimeStepResult:
        return self._run(
            workspace,
            policy,
            RuntimeCommand("build", self._build_command(), self.root_hint),
        )

    def package(self, workspace: Path, policy: ExecutionPolicy) -> RuntimeStepResult:
        return self._run(
            workspace,
            policy,
            RuntimeCommand("package", self._package_command(), self.root_hint),
        )

    def smoke_test(self, workspace: Path, policy: ExecutionPolicy) -> RuntimeStepResult:
        return self._run(
            workspace,
            policy,
            RuntimeCommand("smoke_test", self._smoke_command(), self.root_hint),
        )

    def collect_evidence(
        self, workspace: Path, results: tuple[RuntimeStepResult, ...]
    ) -> RuntimeEvidence:
        required = {
            "prepare",
            "resolve_dependencies",
            "lint",
            "typecheck",
            "test",
            "build",
            "package",
            "smoke_test",
        }
        stages = {result.stage for result in results}
        if stages != required:
            raise SoftwareFactoryError("runtime evidence is incomplete")
        return RuntimeEvidence(
            self.adapter_id,
            _workspace_digest(workspace),
            results,
            all(result.passed for result in results),
        )

    def _run(
        self, workspace: Path, policy: ExecutionPolicy, command: RuntimeCommand
    ) -> RuntimeStepResult:
        root = workspace.resolve()
        working = (root / command.working_directory).resolve()
        if root != working and root not in working.parents:
            raise SoftwareFactoryError("runtime working directory escapes workspace")
        if not working.is_dir():
            raise SoftwareFactoryError("runtime working directory is unavailable")
        return self._boundary.execute(root, command, policy)

    def _runtime_root(self, workspace: Path) -> Path:
        return (workspace.resolve() / self.root_hint).resolve()

    def _prepare_command(self) -> tuple[str, ...]:
        raise NotImplementedError

    def _dependency_command(self) -> tuple[str, ...]:
        raise NotImplementedError

    def _lint_command(self) -> tuple[str, ...]:
        raise NotImplementedError

    def _typecheck_command(self) -> tuple[str, ...]:
        raise NotImplementedError

    def _test_command(self) -> tuple[str, ...]:
        raise NotImplementedError

    def _build_command(self) -> tuple[str, ...]:
        raise NotImplementedError

    def _package_command(self) -> tuple[str, ...]:
        raise NotImplementedError

    def _smoke_command(self) -> tuple[str, ...]:
        raise NotImplementedError


class PythonRuntimeAdapter(_CommandRuntimeAdapter):
    adapter_id = "ilaios.runtime.python"
    manifest_name = "pyproject.toml"
    executable_name = "python"

    def _prepare_command(self) -> tuple[str, ...]:
        return ("python", "-m", "compileall", "-q", "src", "services")

    def _dependency_command(self) -> tuple[str, ...]:
        return ("python", "-m", "pip", "check")

    def _lint_command(self) -> tuple[str, ...]:
        return ("python", "-m", "ruff", "check", "src", "services", "tests")

    def _typecheck_command(self) -> tuple[str, ...]:
        return ("python", "-m", "mypy", "--strict", "src", "tests")

    def _test_command(self) -> tuple[str, ...]:
        return ("python", "-m", "pytest", "-q")

    def _build_command(self) -> tuple[str, ...]:
        return ("python", "-m", "build", "--wheel", "--no-isolation")

    def _package_command(self) -> tuple[str, ...]:
        return ("python", "-m", "build", "--sdist", "--no-isolation")

    def _smoke_command(self) -> tuple[str, ...]:
        return ("python", "-c", "import services.software_factory")


class NodeRuntimeAdapter(_CommandRuntimeAdapter):
    adapter_id = "ilaios.runtime.node"
    manifest_name = "package.json"
    executable_name = "pnpm"
    root_hint = "apps/website"

    def _prepare_command(self) -> tuple[str, ...]:
        return ("pnpm", "--version")

    def _dependency_command(self) -> tuple[str, ...]:
        return (
            "pnpm",
            "install",
            "--offline",
            "--frozen-lockfile",
            "--ignore-scripts",
        )

    def _lint_command(self) -> tuple[str, ...]:
        return ("pnpm", "run", "lint")

    def _typecheck_command(self) -> tuple[str, ...]:
        return ("pnpm", "run", "typecheck")

    def _test_command(self) -> tuple[str, ...]:
        return ("pnpm", "run", "test:site")

    def _build_command(self) -> tuple[str, ...]:
        return ("pnpm", "run", "build")

    def _package_command(self) -> tuple[str, ...]:
        return ("pnpm", "pack", "--dry-run")

    def _smoke_command(self) -> tuple[str, ...]:
        return ("pnpm", "run", "test:site")


class FlutterRuntimeAdapter(_CommandRuntimeAdapter):
    adapter_id = "ilaios.runtime.flutter"
    manifest_name = "pubspec.yaml"
    executable_name = "flutter"
    root_hint = "apps/desktop"

    def __init__(
        self,
        boundary: SecureCommandBoundary,
        *,
        root_hint: str | None = None,
        build_mode: str = "debug",
        package_command: tuple[str, ...] | None = None,
    ) -> None:
        super().__init__(boundary, root_hint=root_hint)
        if build_mode not in {"debug", "release"}:
            raise ValueError("Flutter build_mode must be debug or release")
        if package_command is not None and not package_command:
            raise ValueError("Flutter package_command cannot be empty")
        self._build_mode = build_mode
        self._package_command_override = package_command

    def _prepare_command(self) -> tuple[str, ...]:
        return ("flutter", "--version")

    def _dependency_command(self) -> tuple[str, ...]:
        return ("flutter", "pub", "get", "--offline")

    def _lint_command(self) -> tuple[str, ...]:
        return ("dart", "format", ".")

    def _typecheck_command(self) -> tuple[str, ...]:
        return ("flutter", "analyze")

    def _test_command(self) -> tuple[str, ...]:
        return ("flutter", "test")

    def _build_command(self) -> tuple[str, ...]:
        return ("flutter", "build", "windows", f"--{self._build_mode}")

    def _package_command(self) -> tuple[str, ...]:
        if self._package_command_override is not None:
            return self._package_command_override
        return ("dart", "pub", "publish", "--dry-run")

    def _smoke_command(self) -> tuple[str, ...]:
        return ("flutter", "test", "test/widget_test.dart")


def _workspace_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(
        item for item in root.rglob("*") if item.is_file() and ".git" not in item.parts
    ):
        if _secret_path(path.relative_to(root)):
            raise SoftwareFactoryError(
                "secret-bearing file is outside runtime evidence policy"
            )
        digest.update(path.relative_to(root).as_posix().encode() + b"\0")
        digest.update(path.read_bytes() + b"\0")
    return digest.hexdigest()


def _secret_path(relative: Path) -> bool:
    name = relative.name.casefold()
    return (
        name == ".env"
        or name.startswith(".env.")
        or name in {"id_rsa", "id_ed25519", "credentials.json"}
        or relative.suffix.casefold() in {".pem", ".key", ".p12", ".pfx"}
    )


def evidence_json(evidence: RuntimeEvidence) -> str:
    return json.dumps(
        {
            "adapter_id": evidence.adapter_id,
            "workspace_sha256": evidence.workspace_sha256,
            "passed": evidence.passed,
            "steps": [asdict(result) for result in evidence.steps],
        },
        sort_keys=True,
        separators=(",", ":"),
    )

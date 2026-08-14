"""Canonical SF-5/SF-6 adapters used by the governed SF-7 skill executor."""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from services.software_factory import ExecutionPolicy, SoftwareFactoryError
from services.software_factory_runtime import RuntimeAdapter
from src.code_intelligence import RepositoryAnalyzer


class CanonicalRepositoryIntelligence:
    """Expose existing SF-5 repository intelligence without duplicating analysis."""

    def inspect(self, repository: Path, base_sha: str) -> Mapping[str, object]:
        snapshot = RepositoryAnalyzer(repository.resolve()).snapshot()
        if snapshot.revision != base_sha:
            raise SoftwareFactoryError("repository base SHA changed")
        evidence: dict[str, object] = {
            "revision": snapshot.revision,
            "files": tuple(item.path for item in snapshot.files),
            "symbols": tuple(item.qualified_name for item in snapshot.symbols),
            "api_routes": snapshot.api_routes,
            "schema_entities": snapshot.schema_entities,
            "unknowns": snapshot.unknowns,
        }
        return evidence


class CanonicalRuntimeValidation:
    """Run the existing SF-6 lifecycle only through configured RuntimeAdapters."""

    def __init__(
        self,
        adapters: Mapping[str, RuntimeAdapter],
        policy: ExecutionPolicy,
    ) -> None:
        self._adapters: dict[str, RuntimeAdapter] = dict(adapters)
        self._policy: ExecutionPolicy = policy

    def validate(self, adapter_id: str, repository: Path) -> Mapping[str, object]:
        adapter = self._adapters.get(adapter_id)
        if adapter is None or adapter.adapter_id != adapter_id:
            raise SoftwareFactoryError("canonical runtime adapter is unavailable")
        workspace = repository.resolve()
        results = (
            adapter.prepare(workspace, self._policy),
            adapter.resolve_dependencies(workspace, self._policy),
            adapter.lint(workspace, self._policy),
            adapter.typecheck(workspace, self._policy),
            adapter.test(workspace, self._policy),
            adapter.build(workspace, self._policy),
            adapter.package(workspace, self._policy),
            adapter.smoke_test(workspace, self._policy),
        )
        evidence = adapter.collect_evidence(workspace, results)
        if not evidence.passed:
            raise SoftwareFactoryError("canonical runtime validation failed")
        steps: tuple[dict[str, object], ...] = tuple(
            {
                "stage": result.stage,
                "command": result.command,
                "exit_code": result.exit_code,
                "stdout_sha256": result.stdout_sha256,
                "stderr_sha256": result.stderr_sha256,
                "passed": result.passed,
            }
            for result in evidence.steps
        )
        document: dict[str, object] = {
            "adapter_id": evidence.adapter_id,
            "workspace_sha256": evidence.workspace_sha256,
            "passed": evidence.passed,
            "steps": steps,
        }
        return document

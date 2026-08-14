"""Canonical SF-5/SF-6 adapters used by the governed SF-7 skill executor."""
from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from services.software_factory import ExecutionPolicy, SoftwareFactoryError
from services.software_factory_runtime import RuntimeAdapter, evidence_json
from src.code_intelligence import RepositoryAnalyzer


class CanonicalRepositoryIntelligence:
    """Expose existing SF-5 repository intelligence without duplicating analysis."""
    def inspect(self, repository: Path, base_sha: str) -> Mapping[str, object]:
        snapshot = RepositoryAnalyzer(repository.resolve()).snapshot()
        if snapshot.revision != base_sha:
            raise SoftwareFactoryError("repository base SHA changed")
        return {
            "revision": snapshot.revision,
            "files": tuple(item.path for item in snapshot.files),
            "symbols": tuple(item.qualified_name for item in snapshot.symbols),
            "api_routes": snapshot.api_routes,
            "schema_entities": snapshot.schema_entities,
            "unknowns": snapshot.unknowns,
        }


class CanonicalRuntimeValidation:
    """Run the existing SF-6 lifecycle only through configured RuntimeAdapters."""
    def __init__(self, adapters: Mapping[str, RuntimeAdapter], policy: ExecutionPolicy) -> None:
        self._adapters = dict(adapters)
        self._policy = policy

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
        document = json.loads(evidence_json(evidence))
        if not isinstance(document, dict) or not all(isinstance(key, str) for key in document):
            raise SoftwareFactoryError("canonical runtime evidence is malformed")
        return cast(dict[str, object], document)

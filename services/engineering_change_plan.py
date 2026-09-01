"""Compile provider-backed Engineering output into canonical Software Factory input.

AI text never receives direct filesystem, git, shell, or production authority.
Only a strict JSON change proposal can cross this boundary. The resulting
``SoftwareFactoryRequest`` is still subject to the existing governed Software
Factory, isolated workspace, tenant/policy/grant/finance gates, validation and
review-only promotion boundary.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from services.p0_agent_execution import ProviderBackedAgentResult, binding_for
from services.software_factory import (
    Change,
    ChangeOperation,
    ChangeSet,
    ExecutionPolicy,
    RepositoryRef,
    SoftwareFactoryRequest,
    ValidationPlan,
)


class EngineeringChangePlanError(ValueError):
    """Provider output cannot be represented as a bounded engineering proposal."""


PATCH_CAPABLE_AGENTS = frozenset(
    {
        "ilaios.agent.engineering.core.v1",
        "ilaios.agent.engineering.frontend.v1",
        "ilaios.agent.engineering.backend.v1",
        "ilaios.agent.engineering.integration.v1",
        "ilaios.agent.engineering.test.v1",
        "ilaios.agent.engineering.recovery.v1",
    }
)
NON_MUTATING_ENGINEERING_AGENTS = frozenset(
    {
        "ilaios.agent.engineering.architect.v1",
        "ilaios.agent.engineering.review.v1",
        "ilaios.agent.engineering.runtime-qa.v1",
        "ilaios.agent.engineering.release.v1",
    }
)
_MAX_PROVIDER_OUTPUT_BYTES = 2_000_000
_MAX_CHANGES = 100
_MAX_CONTENT_BYTES = 10_000_000


@dataclass(frozen=True, slots=True)
class EngineeringChangePlan:
    agent_id: str
    request_id: str
    summary: str
    changeset: ChangeSet
    provider_id: str
    model_id: str
    provider_evidence_digest: str

    def to_factory_request(
        self,
        repository_root: Path,
        base_sha: str,
        *,
        allowed_roots: frozenset[str],
    ) -> SoftwareFactoryRequest:
        if not allowed_roots:
            raise EngineeringChangePlanError("engineering patch requires allowed roots")
        return SoftwareFactoryRequest(
            self.request_id,
            RepositoryRef(repository_root.resolve(), base_sha),
            ExecutionPolicy(
                allowed_roots=allowed_roots,
                network_allowed=False,
                secrets_allowed=False,
                secure_mode=True,
                max_files=_MAX_CHANGES,
                max_bytes=_MAX_CONTENT_BYTES,
            ),
            self.changeset,
            ValidationPlan(()),
        )


def compile_engineering_change_plan(
    result: ProviderBackedAgentResult,
    *,
    request_id: str,
) -> EngineeringChangePlan:
    agent_id = result.execution.admission.agent_id
    binding = binding_for(agent_id)
    if agent_id in NON_MUTATING_ENGINEERING_AGENTS:
        raise EngineeringChangePlanError(
            "non-mutating engineering role cannot produce a filesystem change set"
        )
    if agent_id not in PATCH_CAPABLE_AGENTS:
        raise EngineeringChangePlanError("agent is not a patch-capable engineering role")
    if binding.execution_mode != "governed-ai":
        raise EngineeringChangePlanError("engineering patch requires governed AI execution")
    if not request_id or request_id != request_id.strip():
        raise EngineeringChangePlanError("request_id must be non-empty and trimmed")

    output = result.execution.route.get("output")
    if not isinstance(output, dict):
        raise EngineeringChangePlanError("provider route output is missing")
    text = output.get("text")
    if not isinstance(text, str) or not text.strip():
        raise EngineeringChangePlanError("provider did not return a change proposal")
    if len(text.encode("utf-8")) > _MAX_PROVIDER_OUTPUT_BYTES:
        raise EngineeringChangePlanError("provider change proposal exceeds size ceiling")

    document = _strict_json_object(text)
    if set(document) != {"summary", "changes"}:
        raise EngineeringChangePlanError(
            "change proposal has unknown or missing top-level fields"
        )
    summary = document.get("summary")
    raw_changes = document.get("changes")
    if not isinstance(summary, str) or not summary.strip():
        raise EngineeringChangePlanError("change proposal summary is required")
    if not isinstance(raw_changes, list) or not raw_changes:
        raise EngineeringChangePlanError("change proposal requires at least one change")
    if len(raw_changes) > _MAX_CHANGES:
        raise EngineeringChangePlanError("change proposal exceeds file-count ceiling")

    changes = tuple(_parse_change(item) for item in raw_changes)
    total = sum(len(change.content or b"") for change in changes)
    if total > _MAX_CONTENT_BYTES:
        raise EngineeringChangePlanError("change proposal exceeds byte ceiling")
    if len({(change.operation, change.path, change.destination) for change in changes}) != len(changes):
        raise EngineeringChangePlanError("change proposal contains duplicate operations")

    return EngineeringChangePlan(
        agent_id=agent_id,
        request_id=request_id,
        summary=summary.strip(),
        changeset=ChangeSet(changes),
        provider_id=result.provider_id,
        model_id=result.model_id,
        provider_evidence_digest=result.evidence_digest,
    )


def _strict_json_object(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise EngineeringChangePlanError(
            "engineering provider output must be strict JSON, not prose or markdown"
        ) from exc
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise EngineeringChangePlanError(
            "engineering provider output must be a JSON object"
        )
    return value


def _parse_change(value: object) -> Change:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise EngineeringChangePlanError("each change must be an object")
    allowed = {
        "operation",
        "path",
        "content_utf8",
        "destination",
        "expected_sha256",
    }
    if set(value) - allowed:
        raise EngineeringChangePlanError("change contains unknown fields")
    operation_value = value.get("operation")
    path = value.get("path")
    if not isinstance(operation_value, str):
        raise EngineeringChangePlanError("change operation is required")
    try:
        operation = ChangeOperation(operation_value)
    except ValueError as exc:
        raise EngineeringChangePlanError("unsupported change operation") from exc
    if not isinstance(path, str) or not path or path != path.strip():
        raise EngineeringChangePlanError("change path must be non-empty and trimmed")
    _reject_obvious_unbounded_path(path)

    destination = value.get("destination")
    if destination is not None:
        if not isinstance(destination, str) or not destination or destination != destination.strip():
            raise EngineeringChangePlanError("change destination must be trimmed text")
        _reject_obvious_unbounded_path(destination)

    expected_sha256 = value.get("expected_sha256")
    if expected_sha256 is not None and not _is_sha256(expected_sha256):
        raise EngineeringChangePlanError("expected_sha256 must be lowercase SHA-256 hex")

    raw_content = value.get("content_utf8")
    content: bytes | None = None
    if raw_content is not None:
        if not isinstance(raw_content, str):
            raise EngineeringChangePlanError("content_utf8 must be text")
        content = raw_content.encode("utf-8")

    if operation is ChangeOperation.CREATE:
        if content is None or destination is not None or expected_sha256 is not None:
            raise EngineeringChangePlanError("create requires content only")
    elif operation is ChangeOperation.MODIFY:
        if content is None or destination is not None or not _is_sha256(expected_sha256):
            raise EngineeringChangePlanError("modify requires content and expected_sha256")
    elif operation is ChangeOperation.DELETE:
        if content is not None or destination is not None or not _is_sha256(expected_sha256):
            raise EngineeringChangePlanError("delete requires expected_sha256 only")
    elif operation is ChangeOperation.RENAME:
        if content is not None or destination is None or not _is_sha256(expected_sha256):
            raise EngineeringChangePlanError("rename requires destination and expected_sha256")

    return Change(
        operation=operation,
        path=path,
        content=content,
        destination=destination if isinstance(destination, str) else None,
        expected_sha256=expected_sha256 if isinstance(expected_sha256, str) else None,
    )


def _reject_obvious_unbounded_path(path: str) -> None:
    normalized = path.replace("\\", "/")
    parts = normalized.split("/")
    if normalized.startswith("/") or any(part in {"", ".", ".."} for part in parts):
        raise EngineeringChangePlanError(
            "change path is not repository-relative and bounded"
        )
    if ":" in parts[0]:
        raise EngineeringChangePlanError("change path cannot use a drive-qualified root")


def _is_sha256(value: object) -> bool:
    return bool(
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )

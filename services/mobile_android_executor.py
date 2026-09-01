"""Governed downstream Android source-change executor for App Factory requests.

This module does not grant AppFactory direct client mutation authority. It consumes an
already approved Android AppFactory review projection, compiles a tightly bounded
SoftwareFactoryRequest for `apps/mobile/android/<app_id>/...`, and submits only through
the existing governed Software Factory admission path. It does not build, sign, deploy,
submit, publish, call providers, or access Store credentials.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal, Protocol

from services.app_factory import AppRequestProjection
from services.software_factory import (
    Change,
    ChangeOperation,
    ChangeSet,
    ExecutionPolicy,
    FactoryGovernanceContext,
    FactoryJob,
    RepositoryRef,
    SoftwareFactoryRequest,
    ValidationPlan,
)


AndroidSourceOperation = Literal["create", "modify"]


class AndroidImplementationError(ValueError):
    """An Android implementation request is malformed or not admissible."""


class AndroidImplementationPermissionError(PermissionError):
    """An Android implementation operation exceeds this bounded executor."""


class GovernedSoftwareFactoryPort(Protocol):
    """Narrow type port for the existing governed Software Factory authority."""

    def submit(
        self,
        request: SoftwareFactoryRequest,
        context: FactoryGovernanceContext,
    ) -> FactoryJob: ...


@dataclass(frozen=True, slots=True)
class AndroidSourceChange:
    operation: AndroidSourceOperation
    relative_path: str
    content: bytes
    expected_sha256: str | None = None


@dataclass(frozen=True, slots=True)
class AndroidImplementationPlan:
    app_id: str
    application_id: str
    app_request_id: str
    app_request_sha256: str
    objective_sha256: str
    source_changes: tuple[AndroidSourceChange, ...]
    plan_sha256: str


_MAX_ANDROID_FILES = 100
_MAX_ANDROID_BYTES = 10_000_000
_APP_ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{1,127}")
_APPLICATION_ID_PATTERN = re.compile(
    r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+"
)
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_GIT_SHA_PATTERN = re.compile(r"[0-9a-f]{40}")


def build_android_implementation_plan(
    *,
    projection: AppRequestProjection,
    app_id: str,
    application_id: str,
    source_changes: tuple[AndroidSourceChange, ...],
) -> AndroidImplementationPlan:
    """Bind an approved Android AppFactory projection to deterministic source changes."""
    _validate_projection(projection)
    _require_app_id(app_id)
    if _APPLICATION_ID_PATTERN.fullmatch(application_id) is None:
        raise AndroidImplementationError("application_id must be a dotted Android package id")
    if not source_changes:
        raise AndroidImplementationError("at least one Android source change is required")
    if len(source_changes) > _MAX_ANDROID_FILES:
        raise AndroidImplementationError("Android source change count exceeds the bounded limit")

    total_bytes = 0
    seen_paths: set[str] = set()
    canonical_changes: list[dict[str, object]] = []
    for change in source_changes:
        _validate_source_change(change)
        if change.relative_path in seen_paths:
            raise AndroidImplementationError("duplicate Android source path")
        seen_paths.add(change.relative_path)
        total_bytes += len(change.content)
        canonical_changes.append(
            {
                "content_sha256": hashlib.sha256(change.content).hexdigest(),
                "expected_sha256": change.expected_sha256,
                "operation": change.operation,
                "relative_path": change.relative_path,
            }
        )
    if total_bytes > _MAX_ANDROID_BYTES:
        raise AndroidImplementationError("Android source changes exceed the bounded byte limit")

    objective_sha256 = hashlib.sha256(projection["objective"].encode("utf-8")).hexdigest()
    canonical: dict[str, object] = {
        "app_id": app_id,
        "app_request_id": projection["request_id"],
        "app_request_sha256": projection["request_sha256"],
        "application_id": application_id,
        "objective_sha256": objective_sha256,
        "source_changes": canonical_changes,
    }
    plan_sha256 = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return AndroidImplementationPlan(
        app_id=app_id,
        application_id=application_id,
        app_request_id=projection["request_id"],
        app_request_sha256=projection["request_sha256"],
        objective_sha256=objective_sha256,
        source_changes=source_changes,
        plan_sha256=plan_sha256,
    )


def build_android_software_factory_request(
    *,
    plan: AndroidImplementationPlan,
    repository_root: Path,
    base_sha: str,
) -> SoftwareFactoryRequest:
    """Compile an Android plan into the existing review-only Software Factory request."""
    if not repository_root.is_absolute():
        raise AndroidImplementationError("repository_root must be absolute")
    if _GIT_SHA_PATTERN.fullmatch(base_sha) is None:
        raise AndroidImplementationError("base_sha must be a lowercase 40-character git SHA")
    _require_app_id(plan.app_id)
    if _SHA256_PATTERN.fullmatch(plan.plan_sha256) is None:
        raise AndroidImplementationError("plan_sha256 is invalid")

    prefix = f"apps/mobile/android/{plan.app_id}"
    changes: list[Change] = []
    for source_change in plan.source_changes:
        _validate_source_change(source_change)
        operation = (
            ChangeOperation.CREATE
            if source_change.operation == "create"
            else ChangeOperation.MODIFY
        )
        changes.append(
            Change(
                operation=operation,
                path=f"{prefix}/{source_change.relative_path}",
                content=source_change.content,
                expected_sha256=source_change.expected_sha256,
            )
        )

    return SoftwareFactoryRequest(
        request_id=f"android-implementation-{plan.plan_sha256[:20]}",
        repository=RepositoryRef(repository_root, base_sha),
        policy=ExecutionPolicy(
            allowed_roots=frozenset({"apps"}),
            network_allowed=False,
            secrets_allowed=False,
            secure_mode=True,
            max_files=_MAX_ANDROID_FILES,
            max_bytes=_MAX_ANDROID_BYTES,
            timeout_seconds=120,
        ),
        changeset=ChangeSet(tuple(changes)),
        validation_plan=ValidationPlan(),
    )


class GovernedAndroidImplementationExecutor:
    """Submit Android source changes only through the existing governed factory boundary."""

    def __init__(self, governed_factory: GovernedSoftwareFactoryPort) -> None:
        self._governed_factory = governed_factory

    def submit(
        self,
        *,
        plan: AndroidImplementationPlan,
        projection: AppRequestProjection,
        repository_root: Path,
        base_sha: str,
        context: FactoryGovernanceContext,
    ) -> FactoryJob:
        _validate_projection(projection)
        if plan.app_request_id != projection["request_id"]:
            raise AndroidImplementationError("plan request id does not match AppFactory projection")
        if plan.app_request_sha256 != projection["request_sha256"]:
            raise AndroidImplementationError("plan is not bound to the approved AppFactory request")
        objective_sha256 = hashlib.sha256(projection["objective"].encode("utf-8")).hexdigest()
        if plan.objective_sha256 != objective_sha256:
            raise AndroidImplementationError("plan objective binding does not match AppFactory projection")
        request = build_android_software_factory_request(
            plan=plan,
            repository_root=repository_root,
            base_sha=base_sha,
        )
        return self._governed_factory.submit(request, context)

    def build_sign_submit_or_publish(self) -> None:
        raise AndroidImplementationPermissionError(
            "build, signing, deployment, Store submission and publication are outside Phase 2 authority"
        )


def _validate_projection(projection: AppRequestProjection) -> None:
    if projection["platform"] != "android":
        raise AndroidImplementationError("only Android AppFactory projections are accepted")
    if projection["action"] != "client_change_request":
        raise AndroidImplementationError("Android implementation requires client_change_request")
    if projection["approved_for_review"] is not True or not projection["approver"].strip():
        raise AndroidImplementationError("AppFactory request must be approved for review")
    if projection["client_mutated"] is not False:
        raise AndroidImplementationError("AppFactory client_mutated must remain false")
    if not projection["request_id"] or projection["request_id"] != projection["request_id"].strip():
        raise AndroidImplementationError("AppFactory request_id must be non-blank and trimmed")
    if not projection["objective"].strip():
        raise AndroidImplementationError("AppFactory objective must be non-blank")
    if _SHA256_PATTERN.fullmatch(projection["request_sha256"]) is None:
        raise AndroidImplementationError("AppFactory request_sha256 is invalid")


def _validate_source_change(change: AndroidSourceChange) -> None:
    path = PurePosixPath(change.relative_path)
    if (
        not change.relative_path
        or change.relative_path != change.relative_path.strip()
        or "\\" in change.relative_path
        or path.is_absolute()
        or not path.parts
        or ".." in path.parts
        or "" in path.parts
    ):
        raise AndroidImplementationError("Android source path must stay within the app root")
    if change.operation == "create":
        if change.expected_sha256 is not None:
            raise AndroidImplementationError("create changes cannot carry expected_sha256")
    elif change.operation == "modify":
        if change.expected_sha256 is None or _SHA256_PATTERN.fullmatch(change.expected_sha256) is None:
            raise AndroidImplementationError("modify changes require a valid expected_sha256")
    else:
        raise AndroidImplementationError("unsupported Android source operation")


def _require_app_id(app_id: str) -> None:
    if _APP_ID_PATTERN.fullmatch(app_id) is None:
        raise AndroidImplementationError("app_id must be a lowercase bounded path token")

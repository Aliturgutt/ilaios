"""Canonical one-prompt execution coordinator.

This service composes the existing Control Plane, governance, durable grants,
evidence, and verified finished-product adapters. It is not a second runtime or
factory. Routing is deterministic and execution fails closed whenever a selected
capability or requested side effect lacks a verified adapter.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, cast

from services.capability_registry import CAPABILITIES
from services.control_plane.api import ControlPlane
from services.control_plane.proposals import (
    BudgetEnvelope,
    DataClass,
    ProposedTask,
    RiskClass,
)
from services.evidence import EvidenceStore
from services.governance import GateError, GovernedRuntimeGateway
from services.integrations.product_runtime import (
    DurableVideoProductRuntime,
    ProductFinalizationPending,
)
from services.runtime import (
    BlastRadiusBudget,
    DurableGrantPolicy,
    ExecutionGrant,
    SchedulingError,
)
from src.video_automation.models import JobState


class ExecutionCoordinatorError(RuntimeError):
    """Raised when one-prompt work cannot safely advance."""


class ExecutionState(str, Enum):
    RECEIVED = "RECEIVED"
    ROUTED = "ROUTED"
    PLANNED = "PLANNED"
    PENDING_ADMISSION = "PENDING_ADMISSION"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    ADMITTED = "ADMITTED"
    QUEUED = "QUEUED"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    ACCEPTED = "ACCEPTED"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_TERMINAL = "FAILED_TERMINAL"
    CANCELLING = "CANCELLING"
    CANCELLED = "CANCELLED"
    DENIED = "DENIED"
    INTERRUPTED = "INTERRUPTED"


class CapabilityMaturity(str, Enum):
    NO_IMPLEMENTATION = "NO_IMPLEMENTATION"
    IMPLEMENTED_NOT_EXECUTABLE = "IMPLEMENTED_NOT_EXECUTABLE"
    REVIEW_ONLY = "REVIEW_ONLY"
    EXECUTABLE_NOT_VERIFIED = "EXECUTABLE_NOT_VERIFIED"
    VERIFIED_FINISHED_PRODUCT_ADAPTER = "VERIFIED_FINISHED_PRODUCT_ADAPTER"


@dataclass(frozen=True, slots=True)
class AdapterDescriptor:
    adapter_id: str | None
    capability_id: str
    maturity: CapabilityMaturity
    worker_subject: str | None = None
    action: str | None = None
    supports_cancellation: bool = False
    blocker_code: str | None = None


@dataclass(frozen=True, slots=True)
class ExecutionRoute:
    capability_id: str
    adapter_id: str | None


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    routes: tuple[ExecutionRoute, ...]

    @property
    def capability_ids(self) -> tuple[str, ...]:
        return tuple(route.capability_id for route in self.routes)


class ExecutionAdapter(Protocol):
    descriptor: AdapterDescriptor

    def prepare(
        self,
        request_id: str,
        objective: str,
        *,
        token: str,
        principal_id: str,
        tenant_id: str,
        now: datetime,
        risk: str,
        data_class: DataClass,
        budget: BudgetEnvelope,
    ) -> dict[str, object]: ...

    def execute(
        self, request_id: str, grant_id: str, *, token: str, now: datetime
    ) -> dict[str, object]: ...

    def accepted_result(self, request_id: str) -> dict[str, object]: ...

    def state(self, request_id: str) -> dict[str, object]: ...

    def recover_finalizing(
        self, request_id: str, *, token: str, now: datetime
    ) -> dict[str, object]: ...

    def interrupt(
        self,
        request_id: str,
        *,
        token: str,
        now: datetime,
        reason: str,
    ) -> dict[str, object]: ...


_VIDEO = "ilaios.capability.video-media-factory"
_WEB = "ilaios.capability.web-factory"
_APP = "ilaios.capability.app-factory"
_SOFTWARE = "ilaios.capability.software-factory"
_RESEARCH = "ilaios.capability.research-data"
_DOCUMENT = "ilaios.capability.creative-document"
_COMMERCE = "ilaios.capability.commerce-growth"
_PERSONAL = "ilaios.capability.personal-operations"
_SECURITY = "ilaios.capability.security-factory"
_KNOWN_CAPABILITY_IDS = frozenset(item.capability_id for item in CAPABILITIES)
_CAPABILITY_BY_ID = {item.capability_id: item for item in CAPABILITIES}
_STALE_EXECUTION_AFTER = timedelta(minutes=15)
_DEFAULT_DEADLINE = timedelta(minutes=10)
_MAX_ATTEMPTS = 2
_RETRYABLE_PRE_ADAPTER_EXCEPTIONS = (
    SchedulingError,
    TimeoutError,
    sqlite3.OperationalError,
)

_ROUTE_TERMS: tuple[tuple[str, frozenset[str]], ...] = (
    (
        _VIDEO,
        frozenset(
            {
                "video",
                "mp4",
                "reel",
                "reels",
                "short video",
                "tanitim videosu",
                "tanıtım videosu",
                "youtube video",
                "tiktok video",
            }
        ),
    ),
    (
        _WEB,
        frozenset(
            {
                "website",
                "web site",
                "web sitesi",
                "landing page",
                "internet sitesi",
            }
        ),
    ),
    (
        _APP,
        frozenset(
            {
                "mobile app",
                "mobil uygulama",
                "desktop app",
                "masaustu uygulama",
                "masaüstü uygulama",
                "windows app",
                "ios app",
                "android app",
            }
        ),
    ),
    (
        _SOFTWARE,
        frozenset(
            {"software", "yazilim", "yazılım", "codebase", "repository", "repo"}
        ),
    ),
    (
        _RESEARCH,
        frozenset(
            {
                "research",
                "arastir",
                "araştır",
                "dataset",
                "veri analizi",
                "data analysis",
            }
        ),
    ),
    (
        _DOCUMENT,
        frozenset(
            {
                "document",
                "dokuman",
                "doküman",
                "pdf",
                "write a report",
                "rapor hazırla",
                "rapor hazirla",
            }
        ),
    ),
    (
        _COMMERCE,
        frozenset(
            {
                "campaign",
                "kampanya",
                "marketing",
                "pazarlama",
                "sales plan",
                "satış planı",
                "satis plani",
            }
        ),
    ),
    (
        _PERSONAL,
        frozenset(
            {
                "calendar",
                "takvim",
                "reminder",
                "hatirlatici",
                "hatırlatıcı",
                "checklist",
            }
        ),
    ),
    (
        _SECURITY,
        frozenset(
            {
                "security review",
                "guvenlik",
                "güvenlik",
                "sast",
                "threat model",
                "secret scan",
                "security scan",
            }
        ),
    ),
)

_ADAPTER_DESCRIPTORS: dict[str, AdapterDescriptor] = {
    _VIDEO: AdapterDescriptor(
        "video.product-runtime.v1",
        _VIDEO,
        CapabilityMaturity.VERIFIED_FINISHED_PRODUCT_ADAPTER,
        worker_subject="worker-video",
        action="video.execute",
        supports_cancellation=True,
    ),
    _WEB: AdapterDescriptor(
        None,
        _WEB,
        CapabilityMaturity.IMPLEMENTED_NOT_EXECUTABLE,
        blocker_code="GENERAL_PURPOSE_WEB_ADAPTER_UNAVAILABLE",
    ),
    _SOFTWARE: AdapterDescriptor(
        None,
        _SOFTWARE,
        CapabilityMaturity.REVIEW_ONLY,
        blocker_code="SOFTWARE_FACTORY_REVIEW_ONLY",
    ),
    _APP: AdapterDescriptor(
        None,
        _APP,
        CapabilityMaturity.REVIEW_ONLY,
        blocker_code="APP_FACTORY_REVIEW_ONLY",
    ),
    _RESEARCH: AdapterDescriptor(
        None,
        _RESEARCH,
        CapabilityMaturity.IMPLEMENTED_NOT_EXECUTABLE,
        blocker_code="RESEARCH_INPUT_BINDING_UNAVAILABLE",
    ),
    _DOCUMENT: AdapterDescriptor(
        None,
        _DOCUMENT,
        CapabilityMaturity.IMPLEMENTED_NOT_EXECUTABLE,
        blocker_code="DOCUMENT_SOURCE_BINDING_UNAVAILABLE",
    ),
    _COMMERCE: AdapterDescriptor(
        None,
        _COMMERCE,
        CapabilityMaturity.REVIEW_ONLY,
        blocker_code="COMMERCE_FACTORY_REVIEW_ONLY",
    ),
    _PERSONAL: AdapterDescriptor(
        None,
        _PERSONAL,
        CapabilityMaturity.REVIEW_ONLY,
        blocker_code="PERSONAL_OPERATIONS_REVIEW_ONLY",
    ),
    _SECURITY: AdapterDescriptor(
        None,
        _SECURITY,
        CapabilityMaturity.IMPLEMENTED_NOT_EXECUTABLE,
        blocker_code="SECURITY_SCOPE_BINDING_UNAVAILABLE",
    ),
}

_ALLOWED_TRANSITIONS: dict[ExecutionState, frozenset[ExecutionState]] = {
    ExecutionState.RECEIVED: frozenset(
        {ExecutionState.ROUTED, ExecutionState.FAILED_TERMINAL}
    ),
    ExecutionState.ROUTED: frozenset(
        {ExecutionState.PLANNED, ExecutionState.FAILED_TERMINAL}
    ),
    ExecutionState.PLANNED: frozenset(
        {
            ExecutionState.PENDING_ADMISSION,
            ExecutionState.BLOCKED,
            ExecutionState.FAILED_TERMINAL,
        }
    ),
    ExecutionState.PENDING_ADMISSION: frozenset(
        {
            ExecutionState.PENDING_APPROVAL,
            ExecutionState.ADMITTED,
            ExecutionState.BLOCKED,
            ExecutionState.FAILED_TERMINAL,
        }
    ),
    ExecutionState.PENDING_APPROVAL: frozenset(
        {
            ExecutionState.ADMITTED,
            ExecutionState.DENIED,
            ExecutionState.CANCELLING,
        }
    ),
    ExecutionState.ADMITTED: frozenset(
        {
            ExecutionState.QUEUED,
            ExecutionState.CANCELLING,
            ExecutionState.FAILED_TERMINAL,
        }
    ),
    ExecutionState.QUEUED: frozenset(
        {
            ExecutionState.EXECUTING,
            ExecutionState.CANCELLING,
            ExecutionState.FAILED_RETRYABLE,
            ExecutionState.FAILED_TERMINAL,
        }
    ),
    ExecutionState.EXECUTING: frozenset(
        {
            ExecutionState.VERIFYING,
            ExecutionState.FAILED_RETRYABLE,
            ExecutionState.FAILED_TERMINAL,
            ExecutionState.CANCELLING,
            ExecutionState.ACCEPTED,
            ExecutionState.PARTIAL,
            ExecutionState.INTERRUPTED,
        }
    ),
    ExecutionState.VERIFYING: frozenset(
        {
            ExecutionState.ACCEPTED,
            ExecutionState.FAILED_TERMINAL,
            ExecutionState.CANCELLING,
            ExecutionState.INTERRUPTED,
        }
    ),
    ExecutionState.FAILED_RETRYABLE: frozenset(
        {
            ExecutionState.QUEUED,
            ExecutionState.CANCELLING,
            ExecutionState.FAILED_TERMINAL,
        }
    ),
    ExecutionState.CANCELLING: frozenset(
        {
            ExecutionState.CANCELLED,
            ExecutionState.ACCEPTED,
            ExecutionState.FAILED_TERMINAL,
            ExecutionState.INTERRUPTED,
        }
    ),
    ExecutionState.BLOCKED: frozenset({ExecutionState.CANCELLED}),
    ExecutionState.ACCEPTED: frozenset(),
    ExecutionState.PARTIAL: frozenset(),
    ExecutionState.CANCELLED: frozenset(),
    ExecutionState.FAILED_TERMINAL: frozenset(),
    ExecutionState.DENIED: frozenset(),
    ExecutionState.INTERRUPTED: frozenset(),
}

_HIGH_RISK_TERMS = frozenset(
    {
        "publish",
        "production deploy",
        "deploy to production",
        "external mutation",
        "ödeme",
        "odeme",
        "payment",
        "send email",
        "email gönder",
        "email gonder",
        "private data",
        "personal data",
        "sensitive data",
        "kişisel veri",
        "kisisel veri",
    }
)
_SENSITIVE_DATA_TERMS = frozenset(
    {
        "password",
        "secret",
        "api key",
        "token",
        "credit card",
        "kredi kart",
        "health data",
        "sağlık ver",
        "saglik ver",
        "private data",
        "personal data",
        "kişisel veri",
        "kisisel veri",
    }
)
_VIDEO_EXTERNAL_MUTATION_TERMS = frozenset(
    {
        "publish",
        "upload to youtube",
        "youtube'a yükle",
        "youtube'a yukle",
        "post to tiktok",
        "tiktok'a yükle",
        "tiktok'a yukle",
        "production deploy",
        "deploy to production",
    }
)


class _VideoExecutionAdapter:
    descriptor = _ADAPTER_DESCRIPTORS[_VIDEO]

    def __init__(self, runtime: DurableVideoProductRuntime) -> None:
        self._runtime = runtime

    def prepare(
        self,
        request_id: str,
        objective: str,
        *,
        token: str,
        principal_id: str,
        tenant_id: str,
        now: datetime,
        risk: str,
        data_class: DataClass,
        budget: BudgetEnvelope,
    ) -> dict[str, object]:
        return self._runtime.prepare(
            request_id,
            objective,
            token=token,
            now=now,
            requester_id=principal_id,
            tenant_id=tenant_id,
            defer_lease=True,
            risk=risk,
            data_class=data_class,
            budget=budget,
        )

    def execute(
        self, request_id: str, grant_id: str, *, token: str, now: datetime
    ) -> dict[str, object]:
        return self._runtime.execute(request_id, grant_id, token=token, now=now)

    def accepted_result(self, request_id: str) -> dict[str, object]:
        return self._runtime.get_manifest(request_id)

    def state(self, request_id: str) -> dict[str, object]:
        return self._runtime.get_state(request_id)

    def recover_finalizing(
        self, request_id: str, *, token: str, now: datetime
    ) -> dict[str, object]:
        return self._runtime.recover_finalizing(request_id, token=token, now=now)

    def interrupt(
        self,
        request_id: str,
        *,
        token: str,
        now: datetime,
        reason: str,
    ) -> dict[str, object]:
        return self._runtime.interrupt(
            request_id, token=token, now=now, reason=reason
        )


class ExecutionCoordinator:
    """Durably route authenticated intent into existing governed primitives."""

    def __init__(
        self,
        database_path: Path,
        control_plane: ControlPlane,
        governance: GovernedRuntimeGateway,
        grants: DurableGrantPolicy,
        video: DurableVideoProductRuntime,
        evidence: EvidenceStore | None = None,
    ) -> None:
        self._database_path = database_path
        self._control_plane = control_plane
        self._governance = governance
        self._grants = grants
        self._evidence = evidence
        self._adapters: dict[str, ExecutionAdapter] = {
            _VIDEO: _VideoExecutionAdapter(video)
        }
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _migrate(self) -> None:
        """Apply additive, restart-safe coordinator schema migration and backfill."""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS execution_coordinator_schema ("
                "version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS execution_requests ("
                "request_id TEXT PRIMARY KEY, principal_id TEXT NOT NULL, "
                "tenant_id TEXT NOT NULL, objective TEXT NOT NULL, "
                "capability_id TEXT NOT NULL, adapter_id TEXT, "
                "goal_id TEXT NOT NULL, job_id TEXT NOT NULL, "
                "proposal_id TEXT, status TEXT NOT NULL, "
                "result_json TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"
            )
            columns = {
                str(row["name"])
                for row in connection.execute(
                    "PRAGMA table_info(execution_requests)"
                ).fetchall()
            }
            additions = (
                ("plan_json", "TEXT"),
                ("state_version", "INTEGER NOT NULL DEFAULT 0"),
                ("blocker_code", "TEXT"),
                ("error_json", "TEXT"),
                ("attempt", "INTEGER NOT NULL DEFAULT 0"),
                ("max_attempts", f"INTEGER NOT NULL DEFAULT {_MAX_ATTEMPTS}"),
                ("deadline_at", "TEXT"),
                ("result_sha256", "TEXT"),
                ("evidence_json", "TEXT"),
            )
            for name, declaration in additions:
                if name not in columns:
                    connection.execute(
                        f"ALTER TABLE execution_requests ADD COLUMN {name} {declaration}"
                    )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS execution_events ("
                "sequence INTEGER PRIMARY KEY AUTOINCREMENT, "
                "request_id TEXT NOT NULL, state TEXT NOT NULL, "
                "details_json TEXT NOT NULL, occurred_at TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_execution_events_request "
                "ON execution_events(request_id, sequence)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS execution_closure ("
                "request_id TEXT PRIMARY KEY, terminal_status TEXT NOT NULL, "
                "reason TEXT NOT NULL, terminal_at TEXT NOT NULL, "
                "result_sha256 TEXT)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS execution_steps ("
                "request_id TEXT NOT NULL, step_index INTEGER NOT NULL, "
                "step_id TEXT NOT NULL, capability_id TEXT NOT NULL, "
                "adapter_id TEXT NOT NULL, child_request_id TEXT NOT NULL UNIQUE, "
                "dependencies_json TEXT NOT NULL, status TEXT NOT NULL, "
                "prepare_attempt INTEGER NOT NULL DEFAULT 1, "
                "execution_attempt INTEGER NOT NULL DEFAULT 0, "
                "prepared_json TEXT, result_json TEXT, result_sha256 TEXT, "
                "input_evidence_json TEXT NOT NULL DEFAULT '[]', error_json TEXT, "
                "updated_at TEXT NOT NULL, PRIMARY KEY(request_id, step_index))"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_execution_steps_request "
                "ON execution_steps(request_id, step_index)"
            )
            applied_at = datetime.now(timezone.utc).isoformat()
            for version in (1, 2, 3, 4, 5):
                connection.execute(
                    "INSERT OR IGNORE INTO execution_coordinator_schema "
                    "(version, applied_at) VALUES (?, ?)",
                    (version, applied_at),
                )
            rows = connection.execute("SELECT * FROM execution_requests").fetchall()
            for raw_row in rows:
                self._backfill_legacy_row(connection, cast(sqlite3.Row, raw_row))

    @staticmethod
    def _backfill_legacy_row(
        connection: sqlite3.Connection, row: sqlite3.Row
    ) -> None:
        request_id = str(row["request_id"])
        updates: dict[str, object] = {}
        status_map = {
            "BLOCKED_ADAPTER_UNAVAILABLE": ExecutionState.BLOCKED.value,
            "FAILED": ExecutionState.FAILED_TERMINAL.value,
            "APPROVED": ExecutionState.ADMITTED.value,
        }
        legacy_status = str(row["status"])
        if legacy_status in status_map:
            updates["status"] = status_map[legacy_status]
        if row["deadline_at"] is None:
            try:
                anchor = datetime.fromisoformat(str(row["updated_at"]))
            except ValueError:
                anchor = datetime.now(timezone.utc)
            if anchor.tzinfo is None:
                anchor = anchor.replace(tzinfo=timezone.utc)
            updates["deadline_at"] = (anchor + _DEFAULT_DEADLINE).isoformat()
        if row["plan_json"] is None:
            capability_id = str(row["capability_id"])
            descriptor = _ADAPTER_DESCRIPTORS.get(capability_id)
            blockers: list[dict[str, object]] = []
            if descriptor is not None and descriptor.maturity is not (
                CapabilityMaturity.VERIFIED_FINISHED_PRODUCT_ADAPTER
            ):
                blockers.append(
                    {
                        "capability_id": capability_id,
                        "maturity": descriptor.maturity.value,
                        "blocker_code": descriptor.blocker_code,
                    }
                )
            updates["plan_json"] = json.dumps(
                {
                    "capabilities": [capability_id],
                    "routes": [
                        {
                            "capability_id": capability_id,
                            "adapter_id": row["adapter_id"],
                        }
                    ],
                    "blockers": blockers,
                    "risk": "legacy-unknown",
                    "data_class": "legacy-unknown",
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        if row["result_json"] is not None and row["result_sha256"] is None:
            serialized = str(row["result_json"])
            updates["result_sha256"] = hashlib.sha256(
                serialized.encode("utf-8")
            ).hexdigest()
        if updates:
            assignments = ", ".join(f"{name} = ?" for name in updates)
            connection.execute(
                f"UPDATE execution_requests SET {assignments} WHERE request_id = ?",
                (*updates.values(), request_id),
            )

    def prepare(
        self,
        request_id: str,
        objective: str,
        *,
        token: str,
        principal_id: str,
        tenant_id: str,
        now: datetime,
    ) -> dict[str, object]:
        _require_identifier(request_id, "request_id")
        _require_identity_text(principal_id, "principal_id")
        _require_identity_text(tenant_id, "tenant_id")
        _require_objective(objective)
        _require_aware(now, "execution time")

        existing = self._existing_request(request_id)
        if existing is not None:
            if (
                existing["principal_id"] != principal_id
                or existing["tenant_id"] != tenant_id
                or existing["objective"] != objective
            ):
                raise ExecutionCoordinatorError(
                    "execution request identity conflicts with existing content"
                )
            if (
                existing["capability_id"] == "ilaios.capability.multi"
                and existing["status"] == ExecutionState.PENDING_ADMISSION.value
            ):
                return self._continue_multi_prepare(
                    existing, token=token, now=now
                )
            return self.get(
                request_id, principal_id=principal_id, tenant_id=tenant_id
            )

        plan = classify_execution_plan(objective)
        risk, data_class, budget = classify_execution_policy(objective, plan)
        blockers = _plan_blockers(plan) + _scope_blockers(objective, plan)
        routes = plan.routes

        if len(routes) > 1 and not blockers:
            return self._prepare_multi(
                request_id,
                objective,
                plan=plan,
                token=token,
                principal_id=principal_id,
                tenant_id=tenant_id,
                now=now,
                risk=risk,
                data_class=data_class,
                budget=budget,
            )

        if len(routes) == 1 and not blockers:
            route = routes[0]
            adapter = self._adapters.get(route.capability_id)
            if adapter is None or adapter.descriptor.adapter_id != route.adapter_id:
                raise ExecutionCoordinatorError(
                    "verified adapter registry changed during execution"
                )
            prepared = adapter.prepare(
                request_id,
                objective,
                token=token,
                principal_id=principal_id,
                tenant_id=tenant_id,
                now=now,
                risk=str(risk.value),
                data_class=data_class,
                budget=budget,
            )
            goal_id = _result_text(prepared, "goal_id")
            job_id = _result_text(prepared, "job_id")
            proposal_id = _result_text(prepared, "proposal_id")
            admission_decision = str(prepared.get("admission_decision", ""))
            human_approval = bool(prepared.get("human_approval_required", False))
            if admission_decision == "ALLOW" and not human_approval:
                status = ExecutionState.ADMITTED
            elif admission_decision == "REQUIRE_APPROVAL" and human_approval:
                status = ExecutionState.PENDING_APPROVAL
            else:
                raise ExecutionCoordinatorError(
                    "execution adapter returned invalid admission state"
                )
            blocker_code = None
        else:
            goal = self._control_plane.create_goal(token, objective)
            job = self._control_plane.create_job(token, goal.goal_id)
            proposal = self._control_plane.create_proposal(
                token,
                goal.goal_id,
                acceptance_criteria=(
                    "Every required capability and side effect has a verified adapter",
                    "Execution remains fail-closed while any requirement is blocked",
                ),
                risk_class=risk,
                data_class=data_class,
                budget=budget,
                tasks=tuple(
                    ProposedTask(
                        f"capability-{index + 1}",
                        f"Bind {route.capability_id} to a verified execution adapter",
                    )
                    for index, route in enumerate(routes)
                ),
            )
            goal_id = goal.goal_id
            job_id = job.job_id
            proposal_id = str(proposal["proposal_id"])
            status = ExecutionState.BLOCKED
            blocker_code = str(blockers[0]["blocker_code"])

        deadline = now + _DEFAULT_DEADLINE
        plan_json = json.dumps(
            {
                "capabilities": list(plan.capability_ids),
                "routes": [
                    {
                        "capability_id": route.capability_id,
                        "adapter_id": route.adapter_id,
                    }
                    for route in routes
                ],
                "blockers": blockers,
                "risk": str(risk.value),
                "data_class": str(data_class.value),
                "budget": {
                    "max_attempts": budget.max_attempts,
                    "max_runtime_seconds": budget.max_runtime_seconds,
                    "max_external_spend_minor": budget.max_external_spend_minor,
                },
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        timestamp = now.isoformat()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    "INSERT INTO execution_requests "
                    "(request_id, principal_id, tenant_id, objective, capability_id, "
                    "adapter_id, goal_id, job_id, proposal_id, status, result_json, "
                    "created_at, updated_at, plan_json, state_version, blocker_code, "
                    "error_json, attempt, max_attempts, deadline_at, result_sha256, evidence_json) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, 0, ?, NULL, "
                    "0, ?, ?, NULL, NULL)",
                    (
                        request_id,
                        principal_id,
                        tenant_id,
                        objective,
                        routes[0].capability_id
                        if len(routes) == 1
                        else "ilaios.capability.multi",
                        routes[0].adapter_id if len(routes) == 1 else None,
                        goal_id,
                        job_id,
                        proposal_id,
                        str(status.value),
                        timestamp,
                        timestamp,
                        plan_json,
                        blocker_code,
                        _MAX_ATTEMPTS,
                        deadline.isoformat(),
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise ExecutionCoordinatorError(
                    "execution request changed concurrently"
                ) from error
            initial_states = [
                ExecutionState.RECEIVED,
                ExecutionState.ROUTED,
                ExecutionState.PLANNED,
            ]
            if status is not ExecutionState.BLOCKED:
                initial_states.append(ExecutionState.PENDING_ADMISSION)
            initial_states.append(status)
            _validate_state_sequence(initial_states)
            for state in initial_states:
                self._insert_event(
                    connection,
                    request_id,
                    state,
                    {
                        "capabilities": list(plan.capability_ids),
                        "blocker_code": blocker_code,
                    },
                    now,
                )
        self._record_evidence(request_id, status, now)
        return self.get(
            request_id, principal_id=principal_id, tenant_id=tenant_id
        )

    def decide(
        self,
        request_id: str,
        *,
        approver_id: str,
        tenant_id: str,
        decision: str,
        now: datetime,
    ) -> str:
        _require_identity_text(approver_id, "approver_id")
        _require_identity_text(tenant_id, "tenant_id")
        _require_aware(now, "decision time")
        if decision not in {"approved", "denied"}:
            raise ExecutionCoordinatorError(
                "approval decision must be approved or denied"
            )
        row = self._request_row(request_id)
        if row["status"] != ExecutionState.PENDING_APPROVAL.value:
            raise ExecutionCoordinatorError(
                "execution request is not awaiting approval"
            )
        if row["tenant_id"] != tenant_id:
            raise ExecutionCoordinatorError(
                "cross-tenant execution approval denied"
            )
        if row["principal_id"] == approver_id:
            raise ExecutionCoordinatorError(
                "independent human approver is required"
            )
        if row["capability_id"] == "ilaios.capability.multi":
            return self._decide_multi(
                row,
                approver_id=approver_id,
                decision=decision,
                now=now,
            )
        try:
            self._governance.decide(request_id, approver_id, decision)
        except GateError as error:
            raise ExecutionCoordinatorError(str(error)) from error
        target = (
            ExecutionState.ADMITTED
            if decision == "approved"
            else ExecutionState.DENIED
        )
        self._transition(
            request_id,
            ExecutionState.PENDING_APPROVAL,
            target,
            now,
            {"decision": decision, "approver_id": approver_id},
        )
        if target is ExecutionState.DENIED:
            self._record_closure(
                request_id,
                target,
                "governance approval denied",
                now,
            )
        self._record_evidence(request_id, target, now)
        return str(target.value)

    def resume(
        self,
        request_id: str,
        *,
        token: str,
        now: datetime,
        principal_id: str | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, object]:
        _require_aware(now, "execution time")
        row = self._request_row(request_id)
        self._require_owner(row, principal_id=principal_id, tenant_id=tenant_id)
        if row["capability_id"] == "ilaios.capability.multi":
            return self._resume_multi(row, token=token, now=now)
        state = ExecutionState(str(row["status"]))
        if state is ExecutionState.ACCEPTED:
            return self._accepted_result(row)
        if state in {ExecutionState.EXECUTING, ExecutionState.VERIFYING}:
            return self._reconcile_active(row, token=token, now=now)
        if state not in {ExecutionState.ADMITTED, ExecutionState.FAILED_RETRYABLE}:
            raise ExecutionCoordinatorError("execution request is not resumable")

        deadline_at = _stored_datetime(row["deadline_at"], "execution deadline")
        if now >= deadline_at:
            payload = _error_payload(
                "EXECUTION_DEADLINE_EXCEEDED",
                "timeout",
                False,
                "Execution deadline expired before work could resume.",
                "queue",
                int(row["attempt"]),
            )
            self._fail(
                request_id,
                state,
                ExecutionState.FAILED_TERMINAL,
                now,
                payload,
            )
            raise ExecutionCoordinatorError(
                "execution request deadline has expired"
            )

        capability_id = str(row["capability_id"])
        descriptor = _ADAPTER_DESCRIPTORS.get(capability_id)
        adapter = self._adapters.get(capability_id)
        if (
            descriptor is None
            or adapter is None
            or descriptor.maturity
            is not CapabilityMaturity.VERIFIED_FINISHED_PRODUCT_ADAPTER
            or row["adapter_id"] != descriptor.adapter_id
        ):
            raise ExecutionCoordinatorError(
                "selected capability has no verified executable adapter"
            )
        if not self._governance.admission_proven(request_id):
            raise ExecutionCoordinatorError(
                "governed execution admission is required"
            )

        next_attempt = int(row["attempt"]) + 1
        max_attempts = int(row["max_attempts"])
        if next_attempt > max_attempts:
            payload = _error_payload(
                "RETRY_BUDGET_EXHAUSTED",
                "retry_budget",
                False,
                "Execution retry budget is exhausted.",
                "queue",
                int(row["attempt"]),
            )
            self._fail(
                request_id,
                state,
                ExecutionState.FAILED_TERMINAL,
                now,
                payload,
            )
            raise ExecutionCoordinatorError(
                "execution retry budget is exhausted"
            )
        if descriptor.worker_subject is None or descriptor.action is None:
            raise ExecutionCoordinatorError(
                "verified adapter descriptor is incomplete"
            )

        grant_id = _grant_id(request_id, next_attempt)
        grant = ExecutionGrant(
            grant_id,
            descriptor.worker_subject,
            frozenset({descriptor.action}),
            frozenset({str(row["job_id"])}),
            min(now + timedelta(minutes=10), deadline_at),
            BlastRadiusBudget(max_side_effects=1, max_resources=1),
        )
        self._transition(
            request_id,
            state,
            ExecutionState.QUEUED,
            now,
            {"attempt": next_attempt},
            attempt=next_attempt,
        )
        self._transition(
            request_id,
            ExecutionState.QUEUED,
            ExecutionState.EXECUTING,
            now,
            {"attempt": next_attempt, "grant_id": grant_id},
        )

        registered = False
        adapter_started = False
        try:
            self._grants.register(grant)
            registered = True
            adapter_started = True
            manifest = adapter.execute(
                request_id, grant_id, token=token, now=now
            )
            self._transition(
                request_id,
                ExecutionState.EXECUTING,
                ExecutionState.VERIFYING,
                now,
                {"attempt": next_attempt},
            )
            if manifest.get("accepted") is not True:
                raise ExecutionCoordinatorError(
                    "execution adapter did not produce accepted evidence"
                )
            return self._accept(request_id, manifest, now)
        except ProductFinalizationPending:
            self._record_evidence(request_id, ExecutionState.EXECUTING, now)
            raise
        except Exception as error:
            latest = self._request_row(request_id)
            latest_state = ExecutionState(str(latest["status"]))
            if latest_state in {
                ExecutionState.CANCELLING,
                ExecutionState.CANCELLED,
                ExecutionState.ACCEPTED,
                ExecutionState.INTERRUPTED,
            }:
                raise
            retryable = (
                not adapter_started
                and isinstance(error, _RETRYABLE_PRE_ADAPTER_EXCEPTIONS)
                and next_attempt < max_attempts
            )
            target = (
                ExecutionState.FAILED_RETRYABLE
                if retryable
                else ExecutionState.FAILED_TERMINAL
            )
            payload = _error_payload(
                "EXECUTION_ADAPTER_FAILED",
                type(error).__name__,
                retryable,
                "The governed execution adapter failed.",
                "execution" if adapter_started else "grant",
                next_attempt,
            )
            if latest_state in {
                ExecutionState.EXECUTING,
                ExecutionState.VERIFYING,
            }:
                self._fail(request_id, latest_state, target, now, payload)
            raise
        finally:
            if registered:
                self._grants.revoke(grant_id, now=now)

    def cancel(
        self,
        request_id: str,
        *,
        token: str,
        actor_id: str,
        tenant_id: str,
        now: datetime,
    ) -> str:
        _require_identity_text(actor_id, "actor_id")
        _require_identity_text(tenant_id, "tenant_id")
        _require_aware(now, "cancellation time")
        row = self._request_row(request_id)
        self._require_owner(row, principal_id=actor_id, tenant_id=tenant_id)
        if row["capability_id"] == "ilaios.capability.multi":
            return self._cancel_multi(
                row, token=token, actor_id=actor_id, now=now
            )
        state = ExecutionState(str(row["status"]))
        if state is ExecutionState.CANCELLED:
            return str(state.value)
        if state is ExecutionState.ACCEPTED:
            raise ExecutionCoordinatorError(
                "accepted execution results are immutable"
            )
        if state in {
            ExecutionState.FAILED_TERMINAL,
            ExecutionState.DENIED,
            ExecutionState.INTERRUPTED,
            ExecutionState.PARTIAL,
        }:
            raise ExecutionCoordinatorError(
                "terminal execution cannot be cancelled"
            )
        if state is ExecutionState.BLOCKED:
            self._transition(
                request_id,
                state,
                ExecutionState.CANCELLED,
                now,
                {"actor_id": actor_id},
            )
            self._record_closure(
                request_id,
                ExecutionState.CANCELLED,
                "cancelled by authenticated owner",
                now,
            )
            self._record_evidence(request_id, ExecutionState.CANCELLED, now)
            return ExecutionState.CANCELLED.value
        if state not in {
            ExecutionState.PENDING_APPROVAL,
            ExecutionState.ADMITTED,
            ExecutionState.QUEUED,
            ExecutionState.EXECUTING,
            ExecutionState.VERIFYING,
            ExecutionState.FAILED_RETRYABLE,
            ExecutionState.CANCELLING,
        }:
            raise ExecutionCoordinatorError(
                "execution request cannot be cancelled from current state"
            )
        if state is not ExecutionState.CANCELLING:
            self._transition(
                request_id,
                state,
                ExecutionState.CANCELLING,
                now,
                {"actor_id": actor_id},
            )

        attempt = max(1, int(row["attempt"]))
        self._grants.revoke(_grant_id(request_id, attempt), now=now)
        adapter = self._adapters.get(str(row["capability_id"]))
        if adapter is not None and adapter.descriptor.supports_cancellation:
            product = adapter.state(request_id)
            if str(product.get("status", "")) == "finalizing":
                manifest = adapter.recover_finalizing(request_id, token=token, now=now)
                self._accept(
                    request_id,
                    manifest,
                    now,
                    expected_state=ExecutionState.CANCELLING,
                )
                raise ExecutionCoordinatorError(
                    "execution completed before cancellation won the race"
                )
            product = adapter.interrupt(
                request_id,
                token=token,
                now=now,
                reason="cancelled by authenticated execution owner",
            )
            if product.get("status") == "accepted":
                manifest = adapter.accepted_result(request_id)
                self._accept(
                    request_id,
                    manifest,
                    now,
                    expected_state=ExecutionState.CANCELLING,
                )
                raise ExecutionCoordinatorError(
                    "execution completed before cancellation won the race"
                )
        self._transition(
            request_id,
            ExecutionState.CANCELLING,
            ExecutionState.CANCELLED,
            now,
            {"actor_id": actor_id},
        )
        self._record_closure(
            request_id,
            ExecutionState.CANCELLED,
            "cancelled by authenticated owner",
            now,
        )
        self._record_evidence(request_id, ExecutionState.CANCELLED, now)
        return ExecutionState.CANCELLED.value

    def recover_stale(
        self, *, token: str, now: datetime
    ) -> tuple[dict[str, str], ...]:
        """Recover finalizing work immediately; close genuinely stale active work."""
        _require_aware(now, "recovery time")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM execution_requests WHERE status IN (?, ?, ?)",
                (
                    ExecutionState.EXECUTING.value,
                    ExecutionState.VERIFYING.value,
                    ExecutionState.CANCELLING.value,
                ),
            ).fetchall()
        recovered: list[dict[str, str]] = []
        for raw_row in rows:
            row = cast(sqlite3.Row, raw_row)
            state = ExecutionState(str(row["status"]))
            request_id = str(row["request_id"])
            if row["capability_id"] == "ilaios.capability.multi":
                try:
                    result = self._resume_multi(row, token=token, now=now)
                    if result.get("accepted") is True:
                        recovered.append(
                            {
                                "request_id": request_id,
                                "status": ExecutionState.ACCEPTED.value,
                            }
                        )
                except ProductFinalizationPending:
                    pass
                except ExecutionCoordinatorError:
                    updated_at = _stored_datetime(row["updated_at"], "updated_at")
                    if now - updated_at >= _STALE_EXECUTION_AFTER:
                        self._interrupt_multi(row, token=token, now=now)
                        recovered.append(
                            {
                                "request_id": request_id,
                                "status": ExecutionState.INTERRUPTED.value,
                            }
                        )
                continue
            adapter = self._adapters.get(str(row["capability_id"]))
            if adapter is None:
                continue
            product = adapter.state(request_id)
            product_status = str(product.get("status", ""))
            if product_status == "finalizing":
                manifest = adapter.recover_finalizing(request_id, token=token, now=now)
                self._accept(request_id, manifest, now, expected_state=state)
                recovered.append(
                    {"request_id": request_id, "status": ExecutionState.ACCEPTED.value}
                )
                continue
            if product_status == "accepted":
                manifest = adapter.accepted_result(request_id)
                self._accept(request_id, manifest, now, expected_state=state)
                recovered.append(
                    {"request_id": request_id, "status": ExecutionState.ACCEPTED.value}
                )
                continue
            if product_status == "failed":
                payload = _error_payload(
                    "PRODUCT_RUNTIME_FAILED",
                    "product_runtime",
                    False,
                    "The finished-product runtime closed with failure.",
                    "recovery",
                    int(row["attempt"]),
                )
                self._fail(
                    request_id,
                    state,
                    ExecutionState.FAILED_TERMINAL,
                    now,
                    payload,
                )
                recovered.append(
                    {
                        "request_id": request_id,
                        "status": ExecutionState.FAILED_TERMINAL.value,
                    }
                )
                continue
            updated_at = _stored_datetime(row["updated_at"], "updated_at")
            if now - updated_at < _STALE_EXECUTION_AFTER:
                continue
            adapter.interrupt(
                request_id,
                token=token,
                now=now,
                reason="stale coordinator execution interrupted during recovery",
            )
            self._grants.revoke(
                _grant_id(request_id, max(1, int(row["attempt"]))), now=now
            )
            self._transition(
                request_id,
                state,
                ExecutionState.INTERRUPTED,
                now,
                {"recovered": True},
            )
            self._record_closure(
                request_id,
                ExecutionState.INTERRUPTED,
                "stale execution interrupted and subordinate resources closed",
                now,
            )
            self._record_evidence(request_id, ExecutionState.INTERRUPTED, now)
            recovered.append(
                {"request_id": request_id, "status": ExecutionState.INTERRUPTED.value}
            )
        return tuple(recovered)

    def recover(self, *, token: str, now: datetime) -> dict[str, int]:
        recovered = self.recover_stale(token=token, now=now)
        return {
            "recovered": len(recovered),
            "interrupted": sum(
                1
                for item in recovered
                if item["status"] == ExecutionState.INTERRUPTED.value
            ),
        }

    def get(
        self,
        request_id: str,
        *,
        principal_id: str | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, object]:
        row = self._request_row(request_id)
        self._require_owner(row, principal_id=principal_id, tenant_id=tenant_id)
        with self._connect() as connection:
            closure: sqlite3.Row | None = connection.execute(
                "SELECT terminal_status, reason, terminal_at, result_sha256 "
                "FROM execution_closure WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        result: dict[str, object] = {
            "request_id": row["request_id"],
            "principal_id": row["principal_id"],
            "tenant_id": row["tenant_id"],
            "capability_id": row["capability_id"],
            "adapter_id": row["adapter_id"],
            "goal_id": row["goal_id"],
            "job_id": row["job_id"],
            "proposal_id": row["proposal_id"],
            "execution_status": row["status"],
            "state": row["status"],
            "state_version": row["state_version"],
            "attempt": row["attempt"],
            "max_attempts": row["max_attempts"],
            "deadline_at": row["deadline_at"],
            "plan": _load_json_object(row["plan_json"], "stored execution plan"),
            "terminal": closure is not None,
            "terminal_reason": None if closure is None else str(closure["reason"]),
            "terminal_at": None if closure is None else str(closure["terminal_at"]),
            "result_sha256": None
            if closure is None
            else closure["result_sha256"],
        }
        if row["blocker_code"] is not None:
            result["blocker_code"] = row["blocker_code"]
        if row["error_json"] is not None:
            result["error"] = _load_json_object(
                row["error_json"], "stored execution error"
            )
        if row["result_json"] is not None:
            result["result"] = self._accepted_result(row)
        if row["evidence_json"] is not None:
            result["evidence"] = _load_json_object(
                row["evidence_json"], "stored execution evidence"
            )
        if row["capability_id"] == "ilaios.capability.multi":
            result["steps"] = self._multi_step_statuses(request_id)
        return result

    def preview_web(
        self, request_id: str, *, principal_id: str, tenant_id: str, now: datetime
    ) -> dict[str, object]:
        adapter = self._web_delivery_adapter(
            request_id, principal_id=principal_id, tenant_id=tenant_id
        )
        try:
            return cast(dict[str, object], adapter.preview(
                request_id, requester_id=principal_id, tenant_id=tenant_id, now=now
            ))
        except RuntimeError as error:
            raise ExecutionCoordinatorError(str(error)) from error

    def request_web_publish(
        self, request_id: str, *, principal_id: str, tenant_id: str, now: datetime
    ) -> dict[str, object]:
        adapter = self._web_delivery_adapter(
            request_id, principal_id=principal_id, tenant_id=tenant_id
        )
        try:
            return cast(dict[str, object], adapter.request_publish(
                request_id, requester_id=principal_id, tenant_id=tenant_id, now=now
            ))
        except RuntimeError as error:
            raise ExecutionCoordinatorError(str(error)) from error

    def publish_web(
        self, request_id: str, *, principal_id: str, tenant_id: str, now: datetime
    ) -> dict[str, object]:
        adapter = self._web_delivery_adapter(
            request_id, principal_id=principal_id, tenant_id=tenant_id
        )
        try:
            return cast(dict[str, object], adapter.publish(
                request_id, requester_id=principal_id, tenant_id=tenant_id, now=now
            ))
        except RuntimeError as error:
            raise ExecutionCoordinatorError(str(error)) from error

    def web_deployment_history(
        self, request_id: str, *, principal_id: str, tenant_id: str
    ) -> list[dict[str, object]]:
        adapter = self._web_delivery_adapter(
            request_id, principal_id=principal_id, tenant_id=tenant_id
        )
        try:
            return cast(list[dict[str, object]], adapter.deployment_history(
                request_id, requester_id=principal_id, tenant_id=tenant_id
            ))
        except RuntimeError as error:
            raise ExecutionCoordinatorError(str(error)) from error

    def contains(self, request_id: str) -> bool:
        return self._existing_request(request_id) is not None

    def metrics(self) -> dict[str, object]:
        with self._connect() as connection:
            rows = cast(
                list[sqlite3.Row],
                connection.execute(
                    "SELECT status, COUNT(*) AS count FROM execution_requests GROUP BY status"
                ).fetchall(),
            )
            retry_row = connection.execute(
                "SELECT COALESCE(SUM(CASE WHEN attempt > 1 THEN attempt - 1 ELSE 0 END), 0) "
                "FROM execution_requests"
            ).fetchone()
            step_rows = connection.execute(
                "SELECT status, COUNT(*) AS count FROM execution_steps GROUP BY status"
            ).fetchall()
        counts = {str(row["status"]): int(row["count"]) for row in rows}
        retries = 0 if retry_row is None else int(retry_row[0])
        step_counts = {str(row["status"]): int(row["count"]) for row in step_rows}
        active_states = (
            ExecutionState.QUEUED,
            ExecutionState.EXECUTING,
            ExecutionState.VERIFYING,
            ExecutionState.CANCELLING,
        )
        return {
            "states": counts,
            "active": sum(counts.get(state.value, 0) for state in active_states),
            "blocked": counts.get(ExecutionState.BLOCKED.value, 0),
            "accepted": counts.get(ExecutionState.ACCEPTED.value, 0),
            "failed": counts.get(ExecutionState.FAILED_RETRYABLE.value, 0)
            + counts.get(ExecutionState.FAILED_TERMINAL.value, 0),
            "cancelled": counts.get(ExecutionState.CANCELLED.value, 0),
            "interrupted": counts.get(ExecutionState.INTERRUPTED.value, 0),
            "denied": counts.get(ExecutionState.DENIED.value, 0),
            "retry_count": retries,
            "multi_steps": step_counts,
        }

    def adapter_matrix(self) -> tuple[dict[str, object], ...]:
        return tuple(
            {
                "capability_id": capability_id,
                "adapter_id": descriptor.adapter_id,
                "maturity": descriptor.maturity.value,
                "executable": descriptor.maturity
                is CapabilityMaturity.VERIFIED_FINISHED_PRODUCT_ADAPTER,
                "blocker_code": descriptor.blocker_code,
            }
            for capability_id, descriptor in sorted(_ADAPTER_DESCRIPTORS.items())
        )


    def _prepare_multi(
        self,
        request_id: str,
        objective: str,
        *,
        plan: ExecutionPlan,
        token: str,
        principal_id: str,
        tenant_id: str,
        now: datetime,
        risk: RiskClass,
        data_class: DataClass,
        budget: BudgetEnvelope,
    ) -> dict[str, object]:
        """Persist one bounded parent plan, then prepare verified child adapters."""
        routes = plan.routes
        selected = {route.capability_id for route in routes}
        indexes = {route.capability_id: index for index, route in enumerate(routes)}
        tasks: list[ProposedTask] = []
        dependencies_by_step: list[tuple[str, ...]] = []
        for index, route in enumerate(routes):
            definition = _CAPABILITY_BY_ID[route.capability_id]
            dependencies = tuple(
                f"step-{indexes[dependency] + 1}"
                for dependency in sorted(definition.dependencies & selected)
            )
            dependencies_by_step.append(dependencies)
            tasks.append(
                ProposedTask(
                    f"step-{index + 1}",
                    f"Execute verified capability {route.capability_id}",
                    dependencies,
                )
            )
        goal = self._control_plane.create_goal(token, objective)
        job = self._control_plane.create_job(token, goal.goal_id)
        proposal = self._control_plane.create_proposal(
            token,
            goal.goal_id,
            acceptance_criteria=(
                "Every planned capability uses a verified finished-product adapter",
                "Every semantic dependency is accepted before its dependent step starts",
                "Every step result is content-addressed and linked into aggregate evidence",
                "Full acceptance requires every required step to be accepted",
            ),
            risk_class=risk,
            data_class=data_class,
            budget=budget,
            tasks=tuple(tasks),
        )
        plan_json = json.dumps(
            {
                "capabilities": list(plan.capability_ids),
                "routes": [
                    {
                        "capability_id": route.capability_id,
                        "adapter_id": route.adapter_id,
                    }
                    for route in routes
                ],
                "blockers": [],
                "risk": risk.value,
                "data_class": data_class.value,
                "budget": {
                    "max_attempts": budget.max_attempts,
                    "max_runtime_seconds": budget.max_runtime_seconds,
                    "max_external_spend_minor": budget.max_external_spend_minor,
                },
                "routing_basis": "canonical_registry+deterministic_lexical_hints",
                "execution_mode": "bounded_multi_capability_dag_v1",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        timestamp = now.isoformat()
        deadline = now + _DEFAULT_DEADLINE
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO execution_requests "
                "(request_id, principal_id, tenant_id, objective, capability_id, "
                "adapter_id, goal_id, job_id, proposal_id, status, result_json, "
                "created_at, updated_at, plan_json, state_version, blocker_code, "
                "error_json, attempt, max_attempts, deadline_at, result_sha256, evidence_json) "
                "VALUES (?, ?, ?, ?, 'ilaios.capability.multi', NULL, ?, ?, ?, ?, NULL, "
                "?, ?, ?, 0, NULL, NULL, 0, ?, ?, NULL, NULL)",
                (
                    request_id,
                    principal_id,
                    tenant_id,
                    objective,
                    goal.goal_id,
                    job.job_id,
                    str(proposal["proposal_id"]),
                    ExecutionState.PENDING_ADMISSION.value,
                    timestamp,
                    timestamp,
                    plan_json,
                    _MAX_ATTEMPTS,
                    deadline.isoformat(),
                ),
            )
            for index, route in enumerate(routes):
                if route.adapter_id is None:
                    raise ExecutionCoordinatorError(
                        "multi-capability plan contains an unbound adapter"
                    )
                connection.execute(
                    "INSERT INTO execution_steps "
                    "(request_id, step_index, step_id, capability_id, adapter_id, "
                    "child_request_id, dependencies_json, status, prepare_attempt, "
                    "execution_attempt, prepared_json, result_json, result_sha256, "
                    "input_evidence_json, error_json, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, 'PLANNED', 1, 0, NULL, NULL, NULL, '[]', NULL, ?)",
                    (
                        request_id,
                        index,
                        f"step-{index + 1}",
                        route.capability_id,
                        route.adapter_id,
                        f"{request_id}-step-{index + 1}-p1",
                        json.dumps(dependencies_by_step[index], separators=(",", ":")),
                        timestamp,
                    ),
                )
            for state in (
                ExecutionState.RECEIVED,
                ExecutionState.ROUTED,
                ExecutionState.PLANNED,
                ExecutionState.PENDING_ADMISSION,
            ):
                self._insert_event(
                    connection,
                    request_id,
                    state,
                    {"capabilities": list(plan.capability_ids), "multi": True},
                    now,
                )
        self._record_evidence(request_id, ExecutionState.PENDING_ADMISSION, now)
        return self._continue_multi_prepare(
            self._request_row(request_id), token=token, now=now
        )

    def _continue_multi_prepare(
        self,
        row: sqlite3.Row,
        *,
        token: str,
        now: datetime,
    ) -> dict[str, object]:
        request_id = str(row["request_id"])
        plan = _load_json_object(row["plan_json"], "stored multi-capability plan")
        try:
            risk = RiskClass(str(plan["risk"]))
            data_class = DataClass(str(plan["data_class"]))
            budget_value = cast(dict[str, object], plan["budget"])
            budget = BudgetEnvelope(
                int(str(budget_value["max_attempts"])),
                int(str(budget_value["max_runtime_seconds"])),
                int(str(budget_value["max_external_spend_minor"])),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ExecutionCoordinatorError("stored multi-capability policy is malformed") from error

        for step in self._multi_step_rows(request_id):
            status = str(step["status"])
            if status in {"ADMITTED", "PENDING_APPROVAL"}:
                continue
            adapter = self._verified_step_adapter(step)
            if status == "PREPARING":
                old_child = str(step["child_request_id"])
                try:
                    adapter.state(old_child)
                except Exception:
                    pass
                else:
                    try:
                        adapter.interrupt(
                            old_child,
                            token=token,
                            now=now,
                            reason="recovering orphaned multi-capability preparation",
                        )
                    except Exception as error:
                        raise ExecutionCoordinatorError(
                            "orphaned multi-capability preparation cleanup failed"
                        ) from error
                next_prepare = int(step["prepare_attempt"]) + 1
                if next_prepare > _MAX_ATTEMPTS:
                    payload = _error_payload(
                        "MULTI_PREPARE_RETRY_EXHAUSTED",
                        "prepare_recovery",
                        False,
                        "A multi-capability step could not be prepared safely.",
                        "planning",
                        next_prepare - 1,
                    )
                    self._fail(
                        request_id,
                        ExecutionState.PENDING_ADMISSION,
                        ExecutionState.FAILED_TERMINAL,
                        now,
                        payload,
                    )
                    raise ExecutionCoordinatorError(
                        "multi-capability preparation retry budget exhausted"
                    )
                child_request_id = (
                    f"{request_id}-step-{int(step['step_index']) + 1}-p{next_prepare}"
                )
                with self._connect() as connection:
                    connection.execute(
                        "UPDATE execution_steps SET child_request_id=?, status='PLANNED', "
                        "prepare_attempt=?, updated_at=? WHERE request_id=? AND step_index=? "
                        "AND status='PREPARING'",
                        (
                            child_request_id,
                            next_prepare,
                            now.isoformat(),
                            request_id,
                            step["step_index"],
                        ),
                    )
                step = self._multi_step_rows(request_id)[int(step["step_index"])]
                status = "PLANNED"
            if status != "PLANNED":
                raise ExecutionCoordinatorError("multi-capability preparation state is invalid")
            with self._connect() as connection:
                changed = connection.execute(
                    "UPDATE execution_steps SET status='PREPARING', updated_at=? "
                    "WHERE request_id=? AND step_index=? AND status='PLANNED'",
                    (now.isoformat(), request_id, step["step_index"]),
                ).rowcount
            if changed != 1:
                raise ExecutionCoordinatorError("multi-capability preparation changed concurrently")
            try:
                prepared = adapter.prepare(
                    str(step["child_request_id"]),
                    str(row["objective"]),
                    token=token,
                    principal_id=str(row["principal_id"]),
                    tenant_id=str(row["tenant_id"]),
                    now=now,
                    risk=risk.value,
                    data_class=data_class,
                    budget=budget,
                )
                decision = str(prepared.get("admission_decision", ""))
                human = bool(prepared.get("human_approval_required", False))
                if decision == "ALLOW" and not human:
                    target = "ADMITTED"
                elif decision == "REQUIRE_APPROVAL" and human:
                    target = "PENDING_APPROVAL"
                else:
                    raise ExecutionCoordinatorError(
                        "multi-capability adapter returned invalid admission state"
                    )
                serialized = json.dumps(prepared, sort_keys=True, separators=(",", ":"))
                with self._connect() as connection:
                    changed = connection.execute(
                        "UPDATE execution_steps SET status=?, prepared_json=?, updated_at=? "
                        "WHERE request_id=? AND step_index=? AND status='PREPARING'",
                        (
                            target,
                            serialized,
                            now.isoformat(),
                            request_id,
                            step["step_index"],
                        ),
                    ).rowcount
                if changed != 1:
                    raise ExecutionCoordinatorError(
                        "multi-capability prepared state changed concurrently"
                    )
            except Exception as error:
                with self._connect() as connection:
                    connection.execute(
                        "UPDATE execution_steps SET status='FAILED_TERMINAL', error_json=?, "
                        "updated_at=? WHERE request_id=? AND step_index=?",
                        (
                            json.dumps(
                                {
                                    "error_class": type(error).__name__,
                                    "safe_message": "Multi-capability step preparation failed.",
                                },
                                sort_keys=True,
                                separators=(",", ":"),
                            ),
                            now.isoformat(),
                            request_id,
                            step["step_index"],
                        ),
                    )
                payload = _error_payload(
                    "MULTI_STEP_PREPARE_FAILED",
                    type(error).__name__,
                    False,
                    "A required multi-capability step could not be prepared.",
                    "planning",
                    int(step["prepare_attempt"]),
                )
                self._fail(
                    request_id,
                    ExecutionState.PENDING_ADMISSION,
                    ExecutionState.FAILED_TERMINAL,
                    now,
                    payload,
                )
                raise
        steps = self._multi_step_rows(request_id)
        target = (
            ExecutionState.PENDING_APPROVAL
            if any(str(step["status"]) == "PENDING_APPROVAL" for step in steps)
            else ExecutionState.ADMITTED
        )
        current = self._request_row(request_id)
        if current["status"] == ExecutionState.PENDING_ADMISSION.value:
            self._transition(
                request_id,
                ExecutionState.PENDING_ADMISSION,
                target,
                now,
                {"multi": True, "prepared_steps": len(steps)},
            )
            self._record_evidence(request_id, target, now)
        return self.get(
            request_id,
            principal_id=str(row["principal_id"]),
            tenant_id=str(row["tenant_id"]),
        )

    def _decide_multi(
        self,
        row: sqlite3.Row,
        *,
        approver_id: str,
        decision: str,
        now: datetime,
    ) -> str:
        request_id = str(row["request_id"])
        for step in self._multi_step_rows(request_id):
            if step["status"] != "PENDING_APPROVAL":
                continue
            child_request_id = str(step["child_request_id"])
            try:
                self._governance.decide(child_request_id, approver_id, decision)
            except GateError as error:
                raise ExecutionCoordinatorError(str(error)) from error
            target = "ADMITTED" if decision == "approved" else "DENIED"
            with self._connect() as connection:
                changed = connection.execute(
                    "UPDATE execution_steps SET status=?, updated_at=? WHERE request_id=? "
                    "AND step_index=? AND status='PENDING_APPROVAL'",
                    (target, now.isoformat(), request_id, step["step_index"]),
                ).rowcount
            if changed != 1:
                raise ExecutionCoordinatorError("multi-capability approval changed concurrently")
        target_state = (
            ExecutionState.ADMITTED if decision == "approved" else ExecutionState.DENIED
        )
        self._transition(
            request_id,
            ExecutionState.PENDING_APPROVAL,
            target_state,
            now,
            {"decision": decision, "approver_id": approver_id, "multi": True},
        )
        if target_state is ExecutionState.DENIED:
            self._record_closure(
                request_id,
                target_state,
                "multi-capability governance approval denied",
                now,
            )
        self._record_evidence(request_id, target_state, now)
        return target_state.value

    def _resume_multi(
        self,
        row: sqlite3.Row,
        *,
        token: str,
        now: datetime,
    ) -> dict[str, object]:
        request_id = str(row["request_id"])
        state = ExecutionState(str(row["status"]))
        if state is ExecutionState.ACCEPTED:
            return self._accepted_result(row)
        if state not in {
            ExecutionState.ADMITTED,
            ExecutionState.EXECUTING,
            ExecutionState.VERIFYING,
        }:
            raise ExecutionCoordinatorError("multi-capability execution is not resumable")
        deadline_at = _stored_datetime(row["deadline_at"], "execution deadline")
        if now >= deadline_at:
            payload = _error_payload(
                "EXECUTION_DEADLINE_EXCEEDED",
                "timeout",
                False,
                "Multi-capability execution deadline expired.",
                "execution",
                int(row["attempt"]),
            )
            self._fail(
                request_id,
                state,
                ExecutionState.FAILED_TERMINAL,
                now,
                payload,
            )
            raise ExecutionCoordinatorError("multi-capability execution deadline expired")
        if state is ExecutionState.ADMITTED:
            parent_job = self._control_plane.get_job(token, str(row["job_id"]))
            if parent_job.state is JobState.PENDING:
                self._control_plane.transition_job(
                    token,
                    str(row["job_id"]),
                    JobState.RUNNING,
                    reason="bounded multi-capability execution started",
                    now=now,
                )
            next_attempt = int(row["attempt"]) + 1
            self._transition(
                request_id,
                ExecutionState.ADMITTED,
                ExecutionState.QUEUED,
                now,
                {"attempt": next_attempt, "multi": True},
                attempt=next_attempt,
            )
            self._transition(
                request_id,
                ExecutionState.QUEUED,
                ExecutionState.EXECUTING,
                now,
                {"attempt": next_attempt, "multi": True},
            )
            state = ExecutionState.EXECUTING
        if state is ExecutionState.VERIFYING:
            return self._finalize_multi(
                self._request_row(request_id), token=token, now=now
            )

        accepted_hashes: list[str] = []
        for step in self._multi_step_rows(request_id):
            step_id = str(step["step_id"])
            dependencies = tuple(json.loads(str(step["dependencies_json"])))
            current_steps = {str(item["step_id"]): item for item in self._multi_step_rows(request_id)}
            if any(str(current_steps[dependency]["status"]) != "ACCEPTED" for dependency in dependencies):
                raise ExecutionCoordinatorError(
                    f"multi-capability dependency is not accepted for {step_id}"
                )
            if step["status"] == "ACCEPTED":
                if step["result_sha256"] is None:
                    raise ExecutionCoordinatorError("accepted multi-capability step lacks result digest")
                accepted_hashes.append(str(step["result_sha256"]))
                continue
            adapter = self._verified_step_adapter(step)
            if step["status"] == "EXECUTING":
                product = adapter.state(str(step["child_request_id"]))
                product_status = str(product.get("status", ""))
                if product_status == "finalizing":
                    manifest = adapter.recover_finalizing(
                        str(step["child_request_id"]), token=token, now=now
                    )
                    self._store_multi_step_result(step, manifest, now=now)
                    accepted_hashes.append(self._result_digest(manifest))
                    continue
                if product_status == "accepted":
                    manifest = adapter.accepted_result(str(step["child_request_id"]))
                    self._store_multi_step_result(step, manifest, now=now)
                    accepted_hashes.append(self._result_digest(manifest))
                    continue
                if product_status in {"failed", "interrupted"}:
                    self._close_multi_failure(
                        row,
                        step,
                        now=now,
                        token=token,
                        error_class="product_runtime",
                        safe_message="A required multi-capability step closed without acceptance.",
                    )
                    raise ExecutionCoordinatorError("multi-capability step failed")
                updated_at = _stored_datetime(step["updated_at"], "multi step updated_at")
                if now - updated_at < _STALE_EXECUTION_AFTER:
                    raise ExecutionCoordinatorError("multi-capability step is already executing")
                adapter.interrupt(
                    str(step["child_request_id"]),
                    token=token,
                    now=now,
                    reason="stale multi-capability step interrupted during recovery",
                )
                self._close_multi_failure(
                    row,
                    step,
                    now=now,
                    token=token,
                    error_class="stale_execution",
                    safe_message="A stale multi-capability step was interrupted safely.",
                )
                raise ExecutionCoordinatorError("stale multi-capability step interrupted")
            if step["status"] != "ADMITTED":
                raise ExecutionCoordinatorError("multi-capability step is not executable")
            prepared = _load_json_object(step["prepared_json"], "stored step preparation")
            job_id = _result_text(prepared, "job_id")
            execution_attempt = int(step["execution_attempt"]) + 1
            grant_id = _grant_id(str(step["child_request_id"]), execution_attempt)
            input_evidence = json.dumps(accepted_hashes, separators=(",", ":"))
            with self._connect() as connection:
                changed = connection.execute(
                    "UPDATE execution_steps SET status='EXECUTING', execution_attempt=?, "
                    "input_evidence_json=?, updated_at=? WHERE request_id=? AND step_index=? "
                    "AND status='ADMITTED'",
                    (
                        execution_attempt,
                        input_evidence,
                        now.isoformat(),
                        request_id,
                        step["step_index"],
                    ),
                ).rowcount
            if changed != 1:
                raise ExecutionCoordinatorError("multi-capability step changed concurrently")
            descriptor = adapter.descriptor
            if descriptor.worker_subject is None or descriptor.action is None:
                raise ExecutionCoordinatorError("verified multi-capability adapter is incomplete")
            grant = ExecutionGrant(
                grant_id,
                descriptor.worker_subject,
                frozenset({descriptor.action}),
                frozenset({job_id}),
                min(now + timedelta(minutes=10), deadline_at),
                BlastRadiusBudget(max_side_effects=1, max_resources=1),
            )
            registered = False
            try:
                self._grants.register(grant)
                registered = True
                manifest = adapter.execute(
                    str(step["child_request_id"]), grant_id, token=token, now=now
                )
                if manifest.get("accepted") is not True:
                    raise ExecutionCoordinatorError(
                        "multi-capability adapter did not produce accepted evidence"
                    )
                refreshed = self._multi_step_rows(request_id)[int(step["step_index"])]
                self._store_multi_step_result(refreshed, manifest, now=now)
                accepted_hashes.append(self._result_digest(manifest))
            except ProductFinalizationPending:
                self._record_evidence(request_id, ExecutionState.EXECUTING, now)
                raise
            except Exception as error:
                refreshed = self._multi_step_rows(request_id)[int(step["step_index"])]
                self._close_multi_failure(
                    self._request_row(request_id),
                    refreshed,
                    now=now,
                    token=token,
                    error_class=type(error).__name__,
                    safe_message="A required multi-capability execution step failed.",
                )
                raise
            finally:
                if registered:
                    self._grants.revoke(grant_id, now=now)
        current = self._request_row(request_id)
        if current["status"] == ExecutionState.EXECUTING.value:
            self._transition(
                request_id,
                ExecutionState.EXECUTING,
                ExecutionState.VERIFYING,
                now,
                {"multi": True, "accepted_steps": len(accepted_hashes)},
            )
        return self._finalize_multi(self._request_row(request_id), token=token, now=now)

    def _finalize_multi(
        self,
        row: sqlite3.Row,
        *,
        token: str,
        now: datetime,
        expected_state: ExecutionState = ExecutionState.VERIFYING,
    ) -> dict[str, object]:
        request_id = str(row["request_id"])
        steps = self._multi_step_rows(request_id)
        if not steps or any(step["status"] != "ACCEPTED" for step in steps):
            raise ExecutionCoordinatorError("multi-capability finalization requires all steps accepted")
        manifest_steps: list[dict[str, object]] = []
        for step in steps:
            raw = str(step["result_json"])
            digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
            if digest != step["result_sha256"]:
                raise ExecutionCoordinatorError("multi-capability step result integrity check failed")
            result = _load_json_object(raw, "stored multi-capability step result")
            manifest_steps.append(
                {
                    "step_id": step["step_id"],
                    "capability_id": step["capability_id"],
                    "adapter_id": step["adapter_id"],
                    "child_request_id": step["child_request_id"],
                    "dependencies": json.loads(str(step["dependencies_json"])),
                    "input_evidence": json.loads(str(step["input_evidence_json"])),
                    "result_sha256": digest,
                    "result": result,
                }
            )
        parent_job = self._control_plane.get_job(token, str(row["job_id"]))
        if parent_job.state is JobState.PENDING:
            parent_job = self._control_plane.transition_job(
                token,
                str(row["job_id"]),
                JobState.RUNNING,
                reason="multi-capability child evidence recovered",
                now=now,
            )
        if parent_job.state is JobState.RUNNING:
            parent_job = self._control_plane.transition_job(
                token,
                str(row["job_id"]),
                JobState.VALIDATING,
                reason="all multi-capability child acceptance evidence is durable",
                now=now,
            )
        if parent_job.state is JobState.VALIDATING:
            parent_job = self._control_plane.transition_job(
                token,
                str(row["job_id"]),
                JobState.COMPLETED,
                reason="aggregate multi-capability evidence verified",
                now=now,
            )
        if parent_job.state is not JobState.COMPLETED:
            raise ExecutionCoordinatorError("multi-capability coordination job is not completable")
        manifest: dict[str, object] = {
            "manifest_version": "multi.1",
            "request_id": request_id,
            "requester_id": row["principal_id"],
            "tenant_id": row["tenant_id"],
            "execution_mode": "bounded_multi_capability_dag_v1",
            "capabilities": [step["capability_id"] for step in steps],
            "steps": manifest_steps,
            "job_id": row["job_id"],
            "job_state_proven": True,
            "all_steps_accepted": True,
            "deployment_state": "NOT_DEPLOYED",
            "accepted": True,
        }
        return self._accept(
            request_id,
            manifest,
            now,
            expected_state=expected_state,
        )

    def _cancel_multi(
        self,
        row: sqlite3.Row,
        *,
        token: str,
        actor_id: str,
        now: datetime,
    ) -> str:
        request_id = str(row["request_id"])
        state = ExecutionState(str(row["status"]))
        if state is ExecutionState.CANCELLED:
            return str(state.value)
        if state is ExecutionState.ACCEPTED:
            raise ExecutionCoordinatorError("accepted execution results are immutable")
        if state in {
            ExecutionState.FAILED_TERMINAL,
            ExecutionState.DENIED,
            ExecutionState.INTERRUPTED,
            ExecutionState.PARTIAL,
        }:
            raise ExecutionCoordinatorError("terminal execution cannot be cancelled")
        if state is ExecutionState.BLOCKED:
            self._transition(
                request_id, state, ExecutionState.CANCELLED, now, {"actor_id": actor_id, "multi": True}
            )
            self._record_closure(
                request_id, ExecutionState.CANCELLED, "cancelled by authenticated owner", now
            )
            self._record_evidence(request_id, ExecutionState.CANCELLED, now)
            return ExecutionState.CANCELLED.value
        if state is not ExecutionState.CANCELLING:
            self._transition(
                request_id,
                state,
                ExecutionState.CANCELLING,
                now,
                {"actor_id": actor_id, "multi": True},
            )
        for step in self._multi_step_rows(request_id):
            if step["status"] in {"ACCEPTED", "CANCELLED", "DENIED"}:
                continue
            adapter = self._verified_step_adapter(step)
            execution_attempt = int(step["execution_attempt"])
            if execution_attempt > 0:
                self._grants.revoke(
                    _grant_id(str(step["child_request_id"]), execution_attempt), now=now
                )
            product: dict[str, object] | None = None
            try:
                product = adapter.state(str(step["child_request_id"]))
            except Exception:
                product = None
            if product is not None and str(product.get("status", "")) == "finalizing":
                manifest = adapter.recover_finalizing(
                    str(step["child_request_id"]), token=token, now=now
                )
                refreshed = self._multi_step_rows(request_id)[int(step["step_index"])]
                self._store_multi_step_result(refreshed, manifest, now=now)
                continue
            if product is not None and str(product.get("status", "")) == "accepted":
                manifest = adapter.accepted_result(str(step["child_request_id"]))
                refreshed = self._multi_step_rows(request_id)[int(step["step_index"])]
                self._store_multi_step_result(refreshed, manifest, now=now)
                continue
            if product is not None:
                adapter.interrupt(
                    str(step["child_request_id"]),
                    token=token,
                    now=now,
                    reason="cancelled by authenticated multi-capability owner",
                )
            with self._connect() as connection:
                connection.execute(
                    "UPDATE execution_steps SET status='CANCELLED', updated_at=? "
                    "WHERE request_id=? AND step_index=? AND status!='ACCEPTED'",
                    (now.isoformat(), request_id, step["step_index"]),
                )
        steps = self._multi_step_rows(request_id)
        if steps and all(step["status"] == "ACCEPTED" for step in steps):
            self._finalize_multi(
                self._request_row(request_id),
                token=token,
                now=now,
                expected_state=ExecutionState.CANCELLING,
            )
            raise ExecutionCoordinatorError("execution completed before cancellation won the race")
        parent_job = self._control_plane.get_job(token, str(row["job_id"]))
        if parent_job.state not in {JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED}:
            self._control_plane.transition_job(
                token,
                str(row["job_id"]),
                JobState.CANCELLED,
                reason="multi-capability execution cancelled",
                now=now,
            )
        self._transition(
            request_id,
            ExecutionState.CANCELLING,
            ExecutionState.CANCELLED,
            now,
            {"actor_id": actor_id, "multi": True},
        )
        self._record_closure(
            request_id, ExecutionState.CANCELLED, "cancelled by authenticated owner", now
        )
        self._record_evidence(request_id, ExecutionState.CANCELLED, now)
        return ExecutionState.CANCELLED.value

    def _interrupt_multi(
        self,
        row: sqlite3.Row,
        *,
        token: str,
        now: datetime,
    ) -> None:
        request_id = str(row["request_id"])
        state = ExecutionState(str(self._request_row(request_id)["status"]))
        for step in self._multi_step_rows(request_id):
            if step["status"] == "ACCEPTED":
                continue
            adapter = self._verified_step_adapter(step)
            attempt = int(step["execution_attempt"])
            if attempt > 0:
                self._grants.revoke(_grant_id(str(step["child_request_id"]), attempt), now=now)
            try:
                adapter.interrupt(
                    str(step["child_request_id"]),
                    token=token,
                    now=now,
                    reason="stale multi-capability execution interrupted during recovery",
                )
            except Exception:
                pass
            with self._connect() as connection:
                connection.execute(
                    "UPDATE execution_steps SET status='INTERRUPTED', updated_at=? "
                    "WHERE request_id=? AND step_index=? AND status!='ACCEPTED'",
                    (now.isoformat(), request_id, step["step_index"]),
                )
        parent_job = self._control_plane.get_job(token, str(row["job_id"]))
        if parent_job.state not in {JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED}:
            self._control_plane.transition_job(
                token,
                str(row["job_id"]),
                JobState.CANCELLED,
                reason="stale multi-capability coordination interrupted",
                now=now,
            )
        self._transition(
            request_id,
            state,
            ExecutionState.INTERRUPTED,
            now,
            {"recovered": True, "multi": True},
        )
        self._record_closure(
            request_id,
            ExecutionState.INTERRUPTED,
            "stale multi-capability execution interrupted safely",
            now,
        )
        self._record_evidence(request_id, ExecutionState.INTERRUPTED, now)

    def _close_multi_failure(
        self,
        row: sqlite3.Row,
        step: sqlite3.Row,
        *,
        now: datetime,
        token: str,
        error_class: str,
        safe_message: str,
    ) -> None:
        request_id = str(row["request_id"])
        with self._connect() as connection:
            connection.execute(
                "UPDATE execution_steps SET status='FAILED_TERMINAL', error_json=?, updated_at=? "
                "WHERE request_id=? AND step_index=? AND status!='ACCEPTED'",
                (
                    json.dumps(
                        {"error_class": error_class, "safe_message": safe_message},
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    now.isoformat(),
                    request_id,
                    step["step_index"],
                ),
            )
        accepted = any(item["status"] == "ACCEPTED" for item in self._multi_step_rows(request_id))
        current = ExecutionState(str(self._request_row(request_id)["status"]))
        parent_job = self._control_plane.get_job(token, str(row["job_id"]))
        if parent_job.state not in {JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED}:
            self._control_plane.transition_job(
                token,
                str(row["job_id"]),
                JobState.FAILED,
                reason="required multi-capability step failed",
                now=now,
            )
        if accepted:
            self._transition(
                request_id,
                current,
                ExecutionState.PARTIAL,
                now,
                {"failed_step": step["step_id"], "multi": True},
            )
            self._record_closure(
                request_id,
                ExecutionState.PARTIAL,
                "multi-capability execution closed with explicit partial result",
                now,
            )
            self._record_evidence(request_id, ExecutionState.PARTIAL, now)
        else:
            payload = _error_payload(
                "MULTI_STEP_EXECUTION_FAILED",
                error_class,
                False,
                safe_message,
                "execution",
                int(step["execution_attempt"]),
            )
            self._fail(
                request_id,
                current,
                ExecutionState.FAILED_TERMINAL,
                now,
                payload,
            )

    def _store_multi_step_result(
        self,
        step: sqlite3.Row,
        manifest: dict[str, object],
        *,
        now: datetime,
    ) -> None:
        if manifest.get("accepted") is not True:
            raise ExecutionCoordinatorError("unaccepted multi-capability step cannot be committed")
        serialized = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        request_id = str(step["request_id"])
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = connection.execute(
                "SELECT status, result_sha256 FROM execution_steps WHERE request_id=? AND step_index=?",
                (request_id, step["step_index"]),
            ).fetchone()
            if current is None:
                raise ExecutionCoordinatorError("unknown multi-capability step")
            if current["status"] == "ACCEPTED":
                if current["result_sha256"] != digest:
                    raise ExecutionCoordinatorError("accepted multi-capability step result changed")
                return
            if current["status"] != "EXECUTING":
                raise ExecutionCoordinatorError("multi-capability step is not finalizable")
            connection.execute(
                "UPDATE execution_steps SET status='ACCEPTED', result_json=?, result_sha256=?, "
                "updated_at=? WHERE request_id=? AND step_index=? AND status='EXECUTING'",
                (serialized, digest, now.isoformat(), request_id, step["step_index"]),
            )

    def _verified_step_adapter(self, step: sqlite3.Row) -> ExecutionAdapter:
        capability_id = str(step["capability_id"])
        descriptor = _ADAPTER_DESCRIPTORS.get(capability_id)
        adapter = self._adapters.get(capability_id)
        if (
            descriptor is None
            or adapter is None
            or descriptor.maturity is not CapabilityMaturity.VERIFIED_FINISHED_PRODUCT_ADAPTER
            or descriptor.adapter_id != step["adapter_id"]
            or adapter.descriptor.adapter_id != step["adapter_id"]
        ):
            raise ExecutionCoordinatorError("multi-capability step adapter is not verified")
        return adapter

    def _multi_step_rows(self, request_id: str) -> list[sqlite3.Row]:
        with self._connect() as connection:
            return cast(
                list[sqlite3.Row],
                connection.execute(
                    "SELECT * FROM execution_steps WHERE request_id=? ORDER BY step_index",
                    (request_id,),
                ).fetchall(),
            )

    def _multi_step_statuses(self, request_id: str) -> list[dict[str, object]]:
        return [
            {
                "step_id": step["step_id"],
                "capability_id": step["capability_id"],
                "adapter_id": step["adapter_id"],
                "child_request_id": step["child_request_id"],
                "dependencies": json.loads(str(step["dependencies_json"])),
                "status": step["status"],
                "prepare_attempt": step["prepare_attempt"],
                "execution_attempt": step["execution_attempt"],
                "input_evidence": json.loads(str(step["input_evidence_json"])),
                "result_sha256": step["result_sha256"],
            }
            for step in self._multi_step_rows(request_id)
        ]

    @staticmethod
    def _result_digest(manifest: dict[str, object]) -> str:
        serialized = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _reconcile_active(
        self, row: sqlite3.Row, *, token: str, now: datetime
    ) -> dict[str, object]:
        request_id = str(row["request_id"])
        state = ExecutionState(str(row["status"]))
        adapter = self._adapters.get(str(row["capability_id"]))
        if adapter is None:
            raise ExecutionCoordinatorError(
                "active execution adapter is unavailable"
            )
        product = adapter.state(request_id)
        product_status = str(product.get("status", ""))
        if product_status == "finalizing":
            manifest = adapter.recover_finalizing(request_id, token=token, now=now)
            return self._accept(
                request_id,
                manifest,
                now,
                expected_state=state,
            )
        if product_status == "accepted":
            return self._accept(
                request_id,
                adapter.accepted_result(request_id),
                now,
                expected_state=state,
            )
        if product_status == "failed":
            payload = _error_payload(
                "PRODUCT_RUNTIME_FAILED",
                "product_runtime",
                False,
                "The finished-product runtime closed with failure.",
                "recovery",
                int(row["attempt"]),
            )
            self._fail(
                request_id,
                state,
                ExecutionState.FAILED_TERMINAL,
                now,
                payload,
            )
            raise ExecutionCoordinatorError(
                "finished-product runtime failed"
            )
        if product_status == "interrupted":
            self._transition(
                request_id,
                state,
                ExecutionState.INTERRUPTED,
                now,
                {"reconciled": True},
            )
            self._record_closure(
                request_id,
                ExecutionState.INTERRUPTED,
                str(product.get("reason") or "product execution interrupted"),
                now,
            )
            raise ExecutionCoordinatorError(
                "finished-product runtime was interrupted"
            )
        updated_at = _stored_datetime(row["updated_at"], "updated_at")
        if now - updated_at < _STALE_EXECUTION_AFTER:
            raise ExecutionCoordinatorError(
                "execution request is already executing"
            )
        adapter.interrupt(
            request_id,
            token=token,
            now=now,
            reason="stale coordinator execution interrupted during resume",
        )
        self._grants.revoke(
            _grant_id(request_id, max(1, int(row["attempt"]))), now=now
        )
        self._transition(
            request_id,
            state,
            ExecutionState.INTERRUPTED,
            now,
            {"recovered": True},
        )
        self._record_closure(
            request_id,
            ExecutionState.INTERRUPTED,
            "stale execution interrupted and subordinate resources closed",
            now,
        )
        raise ExecutionCoordinatorError(
            "stale execution was interrupted and closed"
        )

    def _existing_request(self, request_id: str) -> sqlite3.Row | None:
        with self._connect() as connection:
            row: sqlite3.Row | None = connection.execute(
                "SELECT * FROM execution_requests WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        return row

    def _request_row(self, request_id: str) -> sqlite3.Row:
        _require_identifier(request_id, "request_id")
        row = self._existing_request(request_id)
        if row is None:
            raise ExecutionCoordinatorError("unknown execution request")
        return row

    def _web_delivery_adapter(
        self, request_id: str, *, principal_id: str, tenant_id: str
    ) -> Any:
        row = self._request_row(request_id)
        self._require_owner(row, principal_id=principal_id, tenant_id=tenant_id)
        if (
            row["capability_id"] != _WEB
            or row["adapter_id"] != "web.product-runtime.v1"
            or row["status"] != ExecutionState.ACCEPTED.value
        ):
            raise ExecutionCoordinatorError("accepted Web execution is required for delivery")
        adapter = self._adapters.get(_WEB)
        if adapter is None or not all(
            callable(getattr(adapter, name, None))
            for name in ("preview", "request_publish", "publish", "deployment_history")
        ):
            raise ExecutionCoordinatorError("canonical Web delivery adapter is unavailable")
        return adapter

    @staticmethod
    def _require_owner(
        row: sqlite3.Row,
        *,
        principal_id: str | None,
        tenant_id: str | None,
    ) -> None:
        if principal_id is not None and row["principal_id"] != principal_id:
            raise ExecutionCoordinatorError(
                "execution does not belong to principal"
            )
        if tenant_id is not None and row["tenant_id"] != tenant_id:
            raise ExecutionCoordinatorError(
                "cross-tenant execution access denied"
            )

    def _transition(
        self,
        request_id: str,
        expected: ExecutionState,
        target: ExecutionState,
        now: datetime,
        details: dict[str, object],
        *,
        attempt: int | None = None,
    ) -> None:
        if target not in _ALLOWED_TRANSITIONS[expected]:
            raise ExecutionCoordinatorError(
                f"illegal execution transition {expected.value}->{target.value}"
            )
        assignments = [
            "status = ?",
            "updated_at = ?",
            "state_version = state_version + 1",
        ]
        values: list[object] = [target.value, now.isoformat()]
        if attempt is not None:
            assignments.append("attempt = ?")
            values.append(attempt)
        values.extend((request_id, expected.value))
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            changed = connection.execute(
                f"UPDATE execution_requests SET {', '.join(assignments)} "
                "WHERE request_id = ? AND status = ?",
                tuple(values),
            ).rowcount
            if changed != 1:
                raise ExecutionCoordinatorError(
                    "execution request changed concurrently"
                )
            self._insert_event(connection, request_id, target, details, now)

    def _fail(
        self,
        request_id: str,
        expected: ExecutionState,
        target: ExecutionState,
        now: datetime,
        error_payload: dict[str, object],
    ) -> None:
        if target not in {
            ExecutionState.FAILED_RETRYABLE,
            ExecutionState.FAILED_TERMINAL,
        }:
            raise ExecutionCoordinatorError("invalid failure target")
        if target not in _ALLOWED_TRANSITIONS[expected]:
            raise ExecutionCoordinatorError("failure transition is not allowed")
        row = self._request_row(request_id)
        error_payload.setdefault("adapter_id", row["adapter_id"])
        error_payload.setdefault("capability_id", row["capability_id"])
        if error_payload.get("evidence_id") is None and row["evidence_json"] is not None:
            evidence = _load_json_object(row["evidence_json"], "stored execution evidence")
            error_payload["evidence_id"] = evidence.get("provenance_hash")
        serialized = json.dumps(
            error_payload, sort_keys=True, separators=(",", ":")
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            changed = connection.execute(
                "UPDATE execution_requests SET status = ?, error_json = ?, "
                "updated_at = ?, state_version = state_version + 1 "
                "WHERE request_id = ? AND status = ?",
                (
                    target.value,
                    serialized,
                    now.isoformat(),
                    request_id,
                    expected.value,
                ),
            ).rowcount
            if changed != 1:
                raise ExecutionCoordinatorError(
                    "execution failure state changed concurrently"
                )
            self._insert_event(connection, request_id, target, error_payload, now)
        if target is ExecutionState.FAILED_TERMINAL:
            self._record_closure(
                request_id,
                target,
                str(error_payload["safe_message"]),
                now,
            )
        self._record_evidence(request_id, target, now)

    def _accept(
        self,
        request_id: str,
        manifest: dict[str, object],
        now: datetime,
        *,
        expected_state: ExecutionState = ExecutionState.VERIFYING,
    ) -> dict[str, object]:
        if manifest.get("accepted") is not True:
            raise ExecutionCoordinatorError(
                "unaccepted adapter manifest cannot be committed"
            )
        if ExecutionState.ACCEPTED not in _ALLOWED_TRANSITIONS[expected_state]:
            raise ExecutionCoordinatorError(
                "acceptance transition is not allowed"
            )
        serialized = json.dumps(
            manifest, sort_keys=True, separators=(",", ":")
        )
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            changed = connection.execute(
                "UPDATE execution_requests SET status = ?, result_json = ?, "
                "result_sha256 = ?, error_json = NULL, updated_at = ?, "
                "state_version = state_version + 1 "
                "WHERE request_id = ? AND status = ?",
                (
                    ExecutionState.ACCEPTED.value,
                    serialized,
                    digest,
                    now.isoformat(),
                    request_id,
                    expected_state.value,
                ),
            ).rowcount
            if changed != 1:
                existing: sqlite3.Row | None = connection.execute(
                    "SELECT * FROM execution_requests WHERE request_id = ?",
                    (request_id,),
                ).fetchone()
                if (
                    existing is not None
                    and existing["status"] == ExecutionState.ACCEPTED.value
                ):
                    return self._accepted_result(existing)
                raise ExecutionCoordinatorError(
                    "execution completion state was lost"
                )
            self._insert_event(
                connection,
                request_id,
                ExecutionState.ACCEPTED,
                {"result_sha256": digest},
                now,
            )
        self._record_closure(
            request_id,
            ExecutionState.ACCEPTED,
            "finished product and acceptance evidence verified",
            now,
            result_sha256=digest,
        )
        self._record_evidence(request_id, ExecutionState.ACCEPTED, now)
        return cast(dict[str, object], json.loads(serialized))

    @staticmethod
    def _accepted_result(row: sqlite3.Row) -> dict[str, object]:
        if row["result_json"] is None or row["result_sha256"] is None:
            raise ExecutionCoordinatorError(
                "accepted execution result is incomplete"
            )
        serialized = str(row["result_json"])
        expected = str(row["result_sha256"])
        actual = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        if actual != expected:
            raise ExecutionCoordinatorError(
                "stored execution result integrity check failed"
            )
        try:
            value = json.loads(serialized)
        except json.JSONDecodeError as error:
            raise ExecutionCoordinatorError(
                "stored execution result is malformed"
            ) from error
        if not isinstance(value, dict):
            raise ExecutionCoordinatorError(
                "stored execution result is malformed"
            )
        return cast(dict[str, object], value)

    def _record_closure(
        self,
        request_id: str,
        status: ExecutionState,
        reason: str,
        now: datetime,
        *,
        result_sha256: str | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO execution_closure "
                "(request_id, terminal_status, reason, terminal_at, result_sha256) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    request_id,
                    status.value,
                    reason[:2048],
                    now.isoformat(),
                    result_sha256,
                ),
            )

    @staticmethod
    def _insert_event(
        connection: sqlite3.Connection,
        request_id: str,
        state: ExecutionState,
        details: dict[str, object],
        now: datetime,
    ) -> None:
        connection.execute(
            "INSERT INTO execution_events "
            "(request_id, state, details_json, occurred_at) VALUES (?, ?, ?, ?)",
            (
                request_id,
                state.value,
                json.dumps(details, sort_keys=True, separators=(",", ":")),
                now.isoformat(),
            ),
        )

    def _record_evidence(
        self, request_id: str, state: ExecutionState, now: datetime
    ) -> None:
        if self._evidence is None:
            return
        row = self._request_row(request_id)
        payload = {
            "request_id": request_id,
            "principal_id": row["principal_id"],
            "tenant_id": row["tenant_id"],
            "state": state.value,
            "capability_id": row["capability_id"],
            "adapter_id": row["adapter_id"],
            "attempt": row["attempt"],
            "occurred_at": now.isoformat(),
        }
        artifact = self._evidence.put_artifact(
            json.dumps(
                payload, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        )
        provenance = self._evidence.append_provenance(
            request_id,
            artifact,
            f"execution_coordinator.{state.value.casefold()}",
        )
        evidence = {
            "artifact_digest": artifact.digest,
            "provenance_hash": provenance.record_hash,
            "state": state.value,
        }
        with self._connect() as connection:
            connection.execute(
                "UPDATE execution_requests SET evidence_json = ? "
                "WHERE request_id = ?",
                (
                    json.dumps(
                        evidence, sort_keys=True, separators=(",", ":")
                    ),
                    request_id,
                ),
            )


def classify_execution_plan(objective: str) -> ExecutionPlan:
    normalized = " ".join(objective.casefold().split())
    if not normalized:
        raise ExecutionCoordinatorError("objective must be non-blank")
    lexical_matches = [
        capability_id
        for capability_id, terms in _ROUTE_TERMS
        if any(_contains_term(normalized, term) for term in terms)
    ]
    registry_matches = [
        definition.capability_id
        for definition in CAPABILITIES
        if definition.domain == "factory"
        and (
            definition.capability_id.casefold() in normalized
            or _contains_term(normalized, definition.display_name)
        )
    ]
    unique = tuple(dict.fromkeys((*registry_matches, *lexical_matches)))
    if not unique:
        raise ExecutionCoordinatorError(
            "one-prompt capability could not be selected with sufficient confidence"
        )
    ordered = _dependency_order(unique)
    return ExecutionPlan(
        tuple(
            ExecutionRoute(
                capability_id,
                _ADAPTER_DESCRIPTORS[capability_id].adapter_id,
            )
            for capability_id in ordered
        )
    )


def classify_execution_route(objective: str) -> ExecutionRoute:
    """Compatibility helper for callers requiring exactly one capability."""
    plan = classify_execution_plan(objective)
    if len(plan.routes) != 1:
        raise ExecutionCoordinatorError(
            "one-prompt request spans multiple capabilities and requires bounded planning"
        )
    return plan.routes[0]


def classify_execution_policy(
    objective: str, plan: ExecutionPlan
) -> tuple[RiskClass, DataClass, BudgetEnvelope]:
    normalized = " ".join(objective.casefold().split())
    risk = (
        RiskClass.HIGH
        if any(_contains_term(normalized, term) for term in _HIGH_RISK_TERMS)
        else RiskClass.MEDIUM
    )
    data_class = (
        DataClass.RESTRICTED
        if any(_contains_term(normalized, term) for term in _SENSITIVE_DATA_TERMS)
        else DataClass.INTERNAL
    )
    task_count = max(1, len(plan.routes))
    return (
        risk,
        data_class,
        BudgetEnvelope(
            task_count,
            min(600, 60 * task_count),
            10 * task_count,
        ),
    )


def _plan_blockers(plan: ExecutionPlan) -> list[dict[str, object]]:
    blockers: list[dict[str, object]] = []
    for route in plan.routes:
        descriptor = _ADAPTER_DESCRIPTORS[route.capability_id]
        if descriptor.maturity is not (
            CapabilityMaturity.VERIFIED_FINISHED_PRODUCT_ADAPTER
        ):
            blockers.append(
                {
                    "capability_id": route.capability_id,
                    "maturity": descriptor.maturity.value,
                    "blocker_code": descriptor.blocker_code
                    or "ADAPTER_UNAVAILABLE",
                }
            )
    return blockers


def _scope_blockers(
    objective: str, plan: ExecutionPlan
) -> list[dict[str, object]]:
    normalized = " ".join(objective.casefold().split())
    external_terms = (
        "production deploy",
        "deploy to production",
        "publish",
        "send email",
        "email gönder",
        "email gonder",
        "payment",
        "ödeme",
        "odeme",
    )
    if not any(_contains_term(normalized, term) for term in external_terms):
        return []
    if _VIDEO in plan.capability_ids and any(
        _contains_term(normalized, term) for term in _VIDEO_EXTERNAL_MUTATION_TERMS
    ):
        return [
            {
                "capability_id": _VIDEO,
                "maturity": CapabilityMaturity.EXECUTABLE_NOT_VERIFIED.value,
                "blocker_code": "VIDEO_EXTERNAL_MUTATION_ADAPTER_UNAVAILABLE",
            }
        ]
    return [
        {
            "capability_id": plan.capability_ids[0],
            "maturity": CapabilityMaturity.EXECUTABLE_NOT_VERIFIED.value,
            "blocker_code": "UNVERIFIED_EXTERNAL_SIDE_EFFECT",
        }
    ]


def _dependency_order(capability_ids: tuple[str, ...]) -> tuple[str, ...]:
    selected = set(capability_ids)
    temporary: set[str] = set()
    permanent: set[str] = set()
    ordered: list[str] = []

    def visit(capability_id: str) -> None:
        if capability_id in permanent:
            return
        if capability_id in temporary:
            raise ExecutionCoordinatorError(
                "selected capability dependencies contain a cycle"
            )
        temporary.add(capability_id)
        definition = _CAPABILITY_BY_ID.get(capability_id)
        if definition is None or capability_id not in _KNOWN_CAPABILITY_IDS:
            raise ExecutionCoordinatorError(
                "selected capability is not canonical"
            )
        for dependency in sorted(definition.dependencies & selected):
            visit(dependency)
        temporary.remove(capability_id)
        permanent.add(capability_id)
        ordered.append(capability_id)

    for capability_id in capability_ids:
        visit(capability_id)
    return tuple(ordered)


def _contains_term(normalized: str, term: str) -> bool:
    pattern = rf"(?<!\w){re.escape(term.casefold())}(?!\w)"
    return re.search(pattern, normalized, flags=re.UNICODE) is not None


def _validate_state_sequence(states: list[ExecutionState]) -> None:
    for left, right in zip(states, states[1:]):
        if right not in _ALLOWED_TRANSITIONS[left]:
            raise ExecutionCoordinatorError(
                f"illegal execution transition {left.value}->{right.value}"
            )


def _grant_id(request_id: str, attempt: int = 1) -> str:
    digest = hashlib.sha256(request_id.encode("utf-8")).hexdigest()[:24]
    base = f"grant-{digest}"
    return base if attempt == 1 else f"{base}-a{attempt}"


def _result_text(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ExecutionCoordinatorError(
            f"execution adapter returned invalid {key}"
        )
    return value


def _error_payload(
    code: str,
    error_class: str,
    retryable: bool,
    safe_message: str,
    failed_stage: str,
    attempt: int,
) -> dict[str, object]:
    return {
        "error_code": code,
        "error_class": error_class,
        "retryable": retryable,
        "safe_message": safe_message,
        "failed_stage": failed_stage,
        "attempt": attempt,
        "evidence_id": None,
    }


def _load_json_object(raw: object, label: str) -> dict[str, object]:
    if raw is None:
        return {}
    try:
        value = json.loads(str(raw))
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise ExecutionCoordinatorError(f"{label} is malformed") from error
    if not isinstance(value, dict):
        raise ExecutionCoordinatorError(f"{label} is malformed")
    return cast(dict[str, object], value)


def _stored_datetime(raw: object, label: str) -> datetime:
    if raw is None:
        raise ExecutionCoordinatorError(f"{label} is unavailable")
    try:
        value = datetime.fromisoformat(str(raw))
    except ValueError as error:
        raise ExecutionCoordinatorError(f"{label} is malformed") from error
    if value.tzinfo is None:
        raise ExecutionCoordinatorError(f"{label} must be timezone-aware")
    return value


def _require_identifier(value: str, field: str) -> None:
    if not value or any(
        character
        not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        for character in value
    ):
        raise ExecutionCoordinatorError(f"invalid {field}")


def _require_identity_text(value: str, field: str) -> None:
    if (
        not value
        or value != value.strip()
        or len(value) > 512
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise ExecutionCoordinatorError(f"invalid {field}")


def _require_objective(objective: str) -> None:
    if not objective or objective != objective.strip():
        raise ExecutionCoordinatorError(
            "objective must be non-blank and trimmed"
        )
    if len(objective) > 20_000:
        raise ExecutionCoordinatorError(
            "objective exceeds one-prompt input limit"
        )


def _require_aware(value: datetime, label: str) -> None:
    if value.tzinfo is None:
        raise ExecutionCoordinatorError(f"{label} must be timezone-aware")

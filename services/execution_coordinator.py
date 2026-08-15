"""Canonical one-prompt execution coordinator.

The coordinator composes existing Control Plane, governance, grant, and
finished-product adapter boundaries. It is not a second runtime or factory.
Capability selection is conservative and execution fails closed when no verified
finished-product adapter exists.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import cast

from services.capability_registry import CAPABILITIES
from services.control_plane.api import ControlPlane
from services.control_plane.proposals import BudgetEnvelope, DataClass, ProposedTask, RiskClass
from services.governance import GateError, GovernedRuntimeGateway
from services.integrations.product_runtime import DurableVideoProductRuntime, ProductRuntimeError
from services.integrations.web_product_runtime import DurableWebProductRuntime, WebProductRuntimeError
from services.runtime import BlastRadiusBudget, DurableGrantPolicy, ExecutionGrant


class ExecutionCoordinatorError(RuntimeError):
    """Raised when one-prompt work cannot safely advance."""


@dataclass(frozen=True, slots=True)
class ExecutionRoute:
    capability_id: str
    adapter_id: str | None


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
_STALE_EXECUTION_AFTER = timedelta(minutes=15)

_ROUTE_TERMS: tuple[tuple[str, frozenset[str]], ...] = (
    (_VIDEO, frozenset({"video", "mp4", "reel", "reels", "short video", "tanitim videosu", "tanıtım videosu", "youtube video", "tiktok video"})),
    (_WEB, frozenset({"website", "web site", "web sitesi", "landing page", "internet sitesi"})),
    (_APP, frozenset({"mobile app", "mobil uygulama", "desktop app", "masaustu uygulama", "masaüstü uygulama", "windows app", "ios app", "android app"})),
    (_SOFTWARE, frozenset({"software", "yazilim", "yazılım", "codebase", "repository"})),
    (_RESEARCH, frozenset({"research", "arastir", "araştır", "dataset", "veri analizi"})),
    (_DOCUMENT, frozenset({"document", "dokuman", "doküman", "report", "rapor", "pdf"})),
    (_COMMERCE, frozenset({"campaign", "kampanya", "marketing", "pazarlama", "sales plan"})),
    (_PERSONAL, frozenset({"calendar", "takvim", "reminder", "hatirlatici", "hatırlatıcı"})),
    (_SECURITY, frozenset({"security review", "guvenlik", "güvenlik", "sast", "threat model"})),
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
        web: DurableWebProductRuntime | None = None,
    ) -> None:
        self._database_path = database_path
        self._control_plane = control_plane
        self._governance = governance
        self._grants = grants
        self._video = video
        self._web = web
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS execution_requests ("
                "request_id TEXT PRIMARY KEY, principal_id TEXT NOT NULL, "
                "tenant_id TEXT NOT NULL, objective TEXT NOT NULL, "
                "capability_id TEXT NOT NULL, adapter_id TEXT, "
                "goal_id TEXT NOT NULL, job_id TEXT NOT NULL, "
                "proposal_id TEXT, status TEXT NOT NULL, "
                "result_json TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS execution_closure ("
                "request_id TEXT PRIMARY KEY, terminal_status TEXT NOT NULL, "
                "reason TEXT NOT NULL, terminal_at TEXT NOT NULL, "
                "result_sha256 TEXT)"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

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
        if not objective or objective != objective.strip():
            raise ExecutionCoordinatorError("objective must be non-blank and trimmed")
        if len(objective) > 20_000:
            raise ExecutionCoordinatorError("objective exceeds one-prompt input limit")
        if now.tzinfo is None:
            raise ExecutionCoordinatorError("execution time must be timezone-aware")
        with self._connect() as connection:
            if connection.execute(
                "SELECT 1 FROM execution_requests WHERE request_id = ?", (request_id,)
            ).fetchone() is not None:
                raise ExecutionCoordinatorError("execution request already exists")

        route = classify_execution_route(objective)
        if route.capability_id == _VIDEO and route.adapter_id == "video.product-runtime.v1":
            prepared = self._video.prepare(
                request_id,
                objective,
                token=token,
                now=now,
                requester_id=principal_id,
                tenant_id=tenant_id,
                defer_lease=True,
            )
            goal_id = _result_text(prepared, "goal_id")
            job_id = _result_text(prepared, "job_id")
            proposal_id = _result_text(prepared, "proposal_id")
            if prepared.get("admission_decision") != "ALLOW":
                raise ExecutionCoordinatorError("video execution was not admitted")
            status = "ADMITTED"
        elif (
            route.capability_id == _WEB
            and route.adapter_id == "web.product-runtime.v1"
            and self._web is not None
        ):
            prepared = self._web.prepare(
                request_id,
                objective,
                token=token,
                now=now,
                requester_id=principal_id,
                tenant_id=tenant_id,
            )
            goal_id = _result_text(prepared, "goal_id")
            job_id = _result_text(prepared, "job_id")
            proposal_id = _result_text(prepared, "proposal_id")
            if prepared.get("admission_decision") != "ALLOW":
                raise ExecutionCoordinatorError("web execution was not admitted")
            status = "ADMITTED"
        else:
            goal = self._control_plane.create_goal(token, objective)
            job = self._control_plane.create_job(token, goal.goal_id)
            proposal = self._control_plane.create_proposal(
                token,
                goal.goal_id,
                acceptance_criteria=(
                    "A governed finished-product adapter is available for the selected capability",
                    "Execution remains blocked until adapter verification exists",
                ),
                risk_class=RiskClass.MEDIUM,
                data_class=DataClass.INTERNAL,
                budget=BudgetEnvelope(1, 60, 0),
                tasks=(
                    ProposedTask(
                        "adapter-binding",
                        f"Bind {route.capability_id} to a verified finished-product adapter",
                    ),
                ),
            )
            goal_id = goal.goal_id
            job_id = job.job_id
            proposal_id = str(proposal["proposal_id"])
            status = "BLOCKED_ADAPTER_UNAVAILABLE"

        result: dict[str, object] = {
            "request_id": request_id,
            "principal_id": principal_id,
            "tenant_id": tenant_id,
            "capability_id": route.capability_id,
            "adapter_id": route.adapter_id,
            "goal_id": goal_id,
            "job_id": job_id,
            "proposal_id": proposal_id,
            "state": "PENDING",
            "execution_status": status,
        }
        timestamp = now.isoformat()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO execution_requests VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)",
                (
                    request_id,
                    principal_id,
                    tenant_id,
                    objective,
                    route.capability_id,
                    route.adapter_id,
                    goal_id,
                    job_id,
                    proposal_id,
                    status,
                    timestamp,
                    timestamp,
                ),
            )
        return result

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
        if now.tzinfo is None:
            raise ExecutionCoordinatorError("decision time must be timezone-aware")
        if decision not in {"approved", "denied"}:
            raise ExecutionCoordinatorError("approval decision must be approved or denied")
        row = self._request_row(request_id)
        if row["status"] != "PENDING_APPROVAL":
            raise ExecutionCoordinatorError("execution request is not awaiting approval")
        if row["tenant_id"] != tenant_id:
            raise ExecutionCoordinatorError("cross-tenant execution approval denied")
        with self._connect() as connection:
            changed = connection.execute(
                "UPDATE execution_requests SET status = 'DECIDING', updated_at = ? "
                "WHERE request_id = ? AND status = 'PENDING_APPROVAL'",
                (now.isoformat(), request_id),
            ).rowcount
        if changed != 1:
            raise ExecutionCoordinatorError("execution request changed concurrently")
        try:
            self._governance.decide(request_id, approver_id, decision)
        except GateError as error:
            with self._connect() as connection:
                connection.execute(
                    "UPDATE execution_requests SET status = 'PENDING_APPROVAL', updated_at = ? "
                    "WHERE request_id = ? AND status = 'DECIDING'",
                    (now.isoformat(), request_id),
                )
            raise ExecutionCoordinatorError(str(error)) from error
        final_status = "APPROVED" if decision == "approved" else "DENIED"
        with self._connect() as connection:
            changed = connection.execute(
                "UPDATE execution_requests SET status = ?, updated_at = ? "
                "WHERE request_id = ? AND status = 'DECIDING'",
                (final_status, now.isoformat(), request_id),
            ).rowcount
            if changed == 1 and final_status == "DENIED":
                self._record_closure(
                    connection,
                    request_id,
                    "DENIED",
                    "governed execution approval denied",
                    now,
                )
        if changed != 1:
            raise ExecutionCoordinatorError("execution decision state was lost")
        return final_status

    def resume(
        self,
        request_id: str,
        *,
        token: str,
        now: datetime,
    ) -> dict[str, object]:
        if now.tzinfo is None:
            raise ExecutionCoordinatorError("execution time must be timezone-aware")
        row = self._request_row(request_id)
        if row["status"] == "ACCEPTED" and row["result_json"] is not None:
            return cast(dict[str, object], json.loads(str(row["result_json"])))
        if row["status"] == "EXECUTING":
            recovered = self._reconcile_executing(row, token=token, now=now)
            if recovered is not None:
                return recovered
            row = self._request_row(request_id)
        current_status = str(row["status"])
        if current_status not in {"ADMITTED", "APPROVED"}:
            raise ExecutionCoordinatorError("execution request is not resumable")

        capability_id = str(row["capability_id"])
        adapter_id = row["adapter_id"]
        is_video = capability_id == _VIDEO and adapter_id == "video.product-runtime.v1"
        is_web = (
            capability_id == _WEB
            and adapter_id == "web.product-runtime.v1"
            and self._web is not None
        )
        if not is_video and not is_web:
            raise ExecutionCoordinatorError("selected capability has no executable adapter")
        if not self._governance.admission_proven(request_id):
            raise ExecutionCoordinatorError("governed execution admission is required")

        job_id = str(row["job_id"])
        grant_id = _grant_id(request_id)
        grant = (
            ExecutionGrant(
                grant_id,
                "worker-video",
                frozenset({"video.execute"}),
                frozenset({job_id}),
                now + timedelta(minutes=10),
                BlastRadiusBudget(max_side_effects=1, max_resources=1),
            )
            if is_video
            else ExecutionGrant(
                grant_id,
                "worker-web",
                frozenset({"web.build"}),
                frozenset({job_id}),
                now + timedelta(minutes=10),
                BlastRadiusBudget(max_side_effects=1, max_resources=1),
            )
        )
        with self._connect() as connection:
            changed = connection.execute(
                "UPDATE execution_requests SET status = 'EXECUTING', updated_at = ? "
                "WHERE request_id = ? AND status = ?",
                (now.isoformat(), request_id, current_status),
            ).rowcount
        if changed != 1:
            raise ExecutionCoordinatorError("execution request changed concurrently")

        grant_registered = False
        try:
            self._grants.register(grant)
            grant_registered = True
            if is_video:
                manifest = self._video.execute(
                    request_id,
                    grant_id,
                    token=token,
                    now=now,
                )
            else:
                web = self._web
                if web is None:
                    raise ExecutionCoordinatorError("web adapter disappeared during execution")
                manifest = web.execute(
                    request_id,
                    grant_id,
                    token=token,
                    now=now,
                )
        except Exception as error:
            reason = _failure_reason(error)
            with self._connect() as connection:
                changed = connection.execute(
                    "UPDATE execution_requests SET status = 'FAILED', updated_at = ? "
                    "WHERE request_id = ? AND status = 'EXECUTING'",
                    (now.isoformat(), request_id),
                ).rowcount
                if changed == 1:
                    self._record_closure(connection, request_id, "FAILED", reason, now)
            raise
        finally:
            if grant_registered:
                self._grants.revoke(grant_id, now=now)

        serialized = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
        result_sha256 = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        with self._connect() as connection:
            changed = connection.execute(
                "UPDATE execution_requests SET status = 'ACCEPTED', result_json = ?, "
                "updated_at = ? WHERE request_id = ? AND status = 'EXECUTING'",
                (serialized, now.isoformat(), request_id),
            ).rowcount
            if changed == 1:
                self._record_closure(
                    connection,
                    request_id,
                    "ACCEPTED",
                    "finished product and acceptance evidence verified",
                    now,
                    result_sha256=result_sha256,
                )
        if changed != 1:
            raise ExecutionCoordinatorError("execution completion state was lost")
        return cast(dict[str, object], json.loads(serialized))

    def recover_stale(
        self,
        *,
        token: str,
        now: datetime,
    ) -> tuple[dict[str, str], ...]:
        if now.tzinfo is None:
            raise ExecutionCoordinatorError("execution time must be timezone-aware")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM execution_requests WHERE status = 'EXECUTING' ORDER BY request_id"
            ).fetchall()
        reconciled: list[dict[str, str]] = []
        for row in rows:
            request_id = str(row["request_id"])
            try:
                result = self._reconcile_executing(
                    cast(sqlite3.Row, row), token=token, now=now
                )
                status = "ACCEPTED" if result is not None else str(
                    self._request_row(request_id)["status"]
                )
            except ExecutionCoordinatorError:
                status = str(self._request_row(request_id)["status"])
            if status != "EXECUTING":
                reconciled.append({"request_id": request_id, "status": status})
        return tuple(reconciled)

    def get(self, request_id: str) -> dict[str, object]:
        row = self._request_row(request_id)
        with self._connect() as connection:
            closure = connection.execute(
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
            "terminal": closure is not None,
            "terminal_reason": None if closure is None else closure["reason"],
            "terminal_at": None if closure is None else closure["terminal_at"],
            "result_sha256": None if closure is None else closure["result_sha256"],
        }
        if row["result_json"] is not None:
            value = json.loads(str(row["result_json"]))
            if not isinstance(value, dict):
                raise ExecutionCoordinatorError("stored execution result is malformed")
            result["result"] = cast(dict[str, object], value)
        return result

    def contains(self, request_id: str) -> bool:
        with self._connect() as connection:
            return connection.execute(
                "SELECT 1 FROM execution_requests WHERE request_id = ?", (request_id,)
            ).fetchone() is not None

    def _reconcile_executing(
        self,
        row: sqlite3.Row,
        *,
        token: str,
        now: datetime,
    ) -> dict[str, object] | None:
        request_id = str(row["request_id"])
        capability_id = str(row["capability_id"])
        adapter_id = row["adapter_id"]
        is_video = capability_id == _VIDEO and adapter_id == "video.product-runtime.v1"
        is_web = (
            capability_id == _WEB
            and adapter_id == "web.product-runtime.v1"
            and self._web is not None
        )
        if not is_video and not is_web:
            raise ExecutionCoordinatorError("executing request has no recoverable adapter")

        if is_video:
            try:
                product_state = self._video.get_state(request_id)
            except ProductRuntimeError as error:
                raise ExecutionCoordinatorError(str(error)) from error
        else:
            web = self._web
            if web is None:
                raise ExecutionCoordinatorError("web adapter is unavailable during recovery")
            try:
                product_state = web.get_state(request_id)
            except WebProductRuntimeError as error:
                raise ExecutionCoordinatorError(str(error)) from error

        if product_state["status"] == "accepted":
            if is_video:
                manifest = self._video.get_manifest(request_id)
            else:
                web = self._web
                if web is None:
                    raise ExecutionCoordinatorError("web adapter is unavailable during recovery")
                manifest = web.get_manifest(request_id)
            serialized = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
            digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
            with self._connect() as connection:
                changed = connection.execute(
                    "UPDATE execution_requests SET status = 'ACCEPTED', result_json = ?, "
                    "updated_at = ? WHERE request_id = ? AND status = 'EXECUTING'",
                    (serialized, now.isoformat(), request_id),
                ).rowcount
                if changed == 1:
                    self._record_closure(
                        connection,
                        request_id,
                        "ACCEPTED",
                        "reconciled durable finished-product acceptance after interruption",
                        now,
                        result_sha256=digest,
                    )
            self._grants.revoke(_grant_id(request_id), now=now)
            return cast(dict[str, object], json.loads(serialized))

        if product_state["status"] == "failed":
            reason = str(product_state.get("reason") or "finished-product runtime failed")
            with self._connect() as connection:
                changed = connection.execute(
                    "UPDATE execution_requests SET status = 'FAILED', updated_at = ? "
                    "WHERE request_id = ? AND status = 'EXECUTING'",
                    (now.isoformat(), request_id),
                ).rowcount
                if changed == 1:
                    self._record_closure(connection, request_id, "FAILED", reason, now)
            self._grants.revoke(_grant_id(request_id), now=now)
            return None

        if product_state["status"] == "interrupted":
            reason = str(product_state.get("reason") or "finished-product execution interrupted")
            with self._connect() as connection:
                changed = connection.execute(
                    "UPDATE execution_requests SET status = 'INTERRUPTED', updated_at = ? "
                    "WHERE request_id = ? AND status = 'EXECUTING'",
                    (now.isoformat(), request_id),
                ).rowcount
                if changed == 1:
                    self._record_closure(connection, request_id, "INTERRUPTED", reason, now)
            self._grants.revoke(_grant_id(request_id), now=now)
            return None

        updated_at = datetime.fromisoformat(str(row["updated_at"]))
        if now - updated_at < _STALE_EXECUTION_AFTER:
            raise ExecutionCoordinatorError("execution request is already executing")
        interruption_reason = (
            "execution exceeded recovery window without durable product terminal evidence"
        )
        try:
            if is_video:
                interrupted = self._video.interrupt(
                    request_id,
                    token=token,
                    now=now,
                    reason=interruption_reason,
                )
            else:
                web = self._web
                if web is None:
                    raise ExecutionCoordinatorError("web adapter is unavailable during recovery")
                interrupted = web.interrupt(
                    request_id,
                    token=token,
                    now=now,
                    reason=interruption_reason,
                )
        except (ProductRuntimeError, WebProductRuntimeError) as error:
            raise ExecutionCoordinatorError(str(error)) from error
        if interrupted["status"] != "interrupted":
            raise ExecutionCoordinatorError("product interruption did not close durably")
        with self._connect() as connection:
            changed = connection.execute(
                "UPDATE execution_requests SET status = 'INTERRUPTED', updated_at = ? "
                "WHERE request_id = ? AND status = 'EXECUTING'",
                (now.isoformat(), request_id),
            ).rowcount
            if changed == 1:
                self._record_closure(
                    connection,
                    request_id,
                    "INTERRUPTED",
                    interruption_reason,
                    now,
                )
        self._grants.revoke(_grant_id(request_id), now=now)
        return None

    @staticmethod
    def _record_closure(
        connection: sqlite3.Connection,
        request_id: str,
        terminal_status: str,
        reason: str,
        now: datetime,
        *,
        result_sha256: str | None = None,
    ) -> None:
        connection.execute(
            "INSERT OR IGNORE INTO execution_closure VALUES (?, ?, ?, ?, ?)",
            (request_id, terminal_status, reason, now.isoformat(), result_sha256),
        )

    def _request_row(self, request_id: str) -> sqlite3.Row:
        _require_identifier(request_id, "request_id")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM execution_requests WHERE request_id = ?", (request_id,)
            ).fetchone()
        if row is None:
            raise ExecutionCoordinatorError("unknown execution request")
        return cast(sqlite3.Row, row)


def classify_execution_route(objective: str) -> ExecutionRoute:
    normalized = " ".join(objective.casefold().split())
    if not normalized:
        raise ExecutionCoordinatorError("objective must be non-blank")
    matches = [
        capability_id
        for capability_id, terms in _ROUTE_TERMS
        if any(term in normalized for term in terms)
    ]
    unique = tuple(dict.fromkeys(matches))
    if not unique:
        raise ExecutionCoordinatorError(
            "one-prompt capability could not be selected with sufficient confidence"
        )
    if len(unique) != 1:
        raise ExecutionCoordinatorError(
            "one-prompt request spans multiple capabilities and requires bounded planning"
        )
    capability_id = unique[0]
    if capability_id not in _KNOWN_CAPABILITY_IDS:
        raise ExecutionCoordinatorError("selected capability is not canonical")
    if capability_id == _VIDEO:
        adapter_id = "video.product-runtime.v1"
    elif capability_id == _WEB:
        adapter_id = "web.product-runtime.v1"
    else:
        adapter_id = None
    return ExecutionRoute(capability_id, adapter_id)


def _grant_id(request_id: str) -> str:
    digest = hashlib.sha256(request_id.encode("utf-8")).hexdigest()[:24]
    return f"grant-{digest}"


def _result_text(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ExecutionCoordinatorError(f"execution adapter returned invalid {key}")
    return value


def _failure_reason(error: Exception) -> str:
    message = " ".join(str(error).split())
    if not message:
        message = "execution failed without an error message"
    return f"{type(error).__name__}: {message}"[:2048]


def _require_identifier(value: str, field: str) -> None:
    if not value or any(
        character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
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

"""Bounded Personal Operations Factory with governed external execution handoff."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import TypedDict

from services.evidence import EvidenceStore
from services.identity import AccessRequest, AuthorizationEngine, Principal
from services.integrations.personal_operations import ConnectorReceipt
from services.runtime.grants import ExecutionGrant, GrantPolicy
from src.core.audit_engine import AuditEngine
from src.core.tool_gateway import ToolGateway


class PersonalOperationsError(PermissionError):
    """Personal operations work violates a bounded authority or approval gate."""


_REVIEW_ACTIONS = frozenset(
    {
        "calendar_draft",
        "checklist_draft",
        "email_draft",
        "note_draft",
        "reminder_draft",
    }
)
_MUTATION_ACTIONS = frozenset(
    {
        "send_email",
        "create_calendar_event",
        "update_calendar_event",
        "create_note",
        "create_reminder",
    }
)
_ALLOWED_ACTIONS = _REVIEW_ACTIONS | _MUTATION_ACTIONS
_EXECUTION_ACTION = "personal-operations.execute"


class OperationStepProjection(TypedDict):
    step_id: str
    action: str
    target: str
    payload_sha256: str


class OperationReviewProjection(TypedDict):
    plan_id: str
    objective: str
    plan_sha256: str
    approved_for_review: bool
    approver: str
    external_applied: bool
    steps: tuple[OperationStepProjection, ...]


@dataclass(frozen=True, slots=True)
class OperationStep:
    step_id: str
    action: str
    target: str
    payload: str
    payload_sha256: str


@dataclass(frozen=True, slots=True)
class OperationPlan:
    plan_id: str
    objective: str
    steps: tuple[OperationStep, ...]
    plan_sha256: str
    approved_for_review: bool
    approver: str | None
    external_applied: bool = False


@dataclass(frozen=True, slots=True)
class ExternalExecutionContext:
    principal: Principal
    access_request: AccessRequest
    execution_grant: ExecutionGrant
    target_account: str
    now: datetime


@dataclass(frozen=True, slots=True)
class ExternalExecutionReceipt:
    plan_id: str
    target_account: str
    receipts: tuple[ConnectorReceipt, ...]


class _ExecutionStore:
    """Durable idempotency store for provider-side mutation receipts."""

    def __init__(self, database_path: Path) -> None:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self._database_path = database_path
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS personal_operation_execution ("
                "execution_key TEXT PRIMARY KEY, receipt_json TEXT NOT NULL)"
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._database_path)

    def get(self, execution_key: str) -> ConnectorReceipt | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT receipt_json FROM personal_operation_execution WHERE execution_key = ?",
                (execution_key,),
            ).fetchone()
        if row is None:
            return None
        payload = json.loads(str(row[0]))
        return ConnectorReceipt(
            provider=str(payload["provider"]),
            provider_id=str(payload["provider_id"]),
            occurred_at=datetime.fromisoformat(str(payload["occurred_at"])),
            target_account=str(payload["target_account"]),
            outcome=str(payload["outcome"]),
        )

    def put(self, execution_key: str, receipt: ConnectorReceipt) -> None:
        payload = json.dumps(
            {
                "provider": receipt.provider,
                "provider_id": receipt.provider_id,
                "occurred_at": receipt.occurred_at.isoformat(),
                "target_account": receipt.target_account,
                "outcome": receipt.outcome,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        with self._connect() as connection:
            try:
                connection.execute(
                    "INSERT INTO personal_operation_execution VALUES (?, ?)",
                    (execution_key, payload),
                )
            except sqlite3.IntegrityError as error:
                raise PersonalOperationsError("execution receipt already persisted") from error


class PersonalOperationsFactory:
    """Create review plans and hand approved mutations to canonical governed execution."""

    def __init__(self, execution_database: Path | None = None) -> None:
        self._plans: dict[str, OperationPlan] = {}
        self._execution_store = None if execution_database is None else _ExecutionStore(execution_database)

    def propose(
        self,
        plan_id: str,
        *,
        objective: str,
        steps: tuple[tuple[str, str, str, str], ...],
    ) -> OperationPlan:
        _require_id(plan_id, "plan_id")
        _require_text(objective, "objective")
        if plan_id in self._plans:
            raise PersonalOperationsError("plan_id already exists")
        if not steps:
            raise PersonalOperationsError("operation plan requires at least one step")

        normalized_steps: list[OperationStep] = []
        seen_ids: set[str] = set()
        for step_id, action, target, payload in steps:
            _require_id(step_id, "step_id")
            _require_text(action, "action")
            _require_text(target, "target")
            _require_text(payload, "payload")
            if step_id in seen_ids:
                raise PersonalOperationsError("step_id must be unique within a plan")
            if action not in _ALLOWED_ACTIONS:
                raise PersonalOperationsError(f"unsupported personal operation action: {action}")
            seen_ids.add(step_id)
            normalized_steps.append(
                OperationStep(
                    step_id=step_id,
                    action=action,
                    target=target.strip(),
                    payload=payload,
                    payload_sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
                )
            )

        canonical = json.dumps(
            {
                "objective": objective.strip(),
                "steps": tuple(
                    {
                        "action": step.action,
                        "payload_sha256": step.payload_sha256,
                        "step_id": step.step_id,
                        "target": step.target,
                    }
                    for step in normalized_steps
                ),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        plan = OperationPlan(
            plan_id=plan_id,
            objective=objective.strip(),
            steps=tuple(normalized_steps),
            plan_sha256=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            approved_for_review=False,
            approver=None,
        )
        self._plans[plan_id] = plan
        return plan

    def approve_for_review(self, plan_id: str, *, approver: str) -> OperationPlan:
        _require_text(approver, "approver")
        plan = self._plans.get(plan_id)
        if plan is None:
            raise PersonalOperationsError("operation plan does not exist")
        if plan.approved_for_review:
            raise PersonalOperationsError("operation plan already approved for review")
        approved = replace(plan, approved_for_review=True, approver=approver.strip())
        self._plans[plan_id] = approved
        return approved

    def review_projection(self, plan_id: str) -> OperationReviewProjection:
        plan = self._plans.get(plan_id)
        if plan is None:
            raise PersonalOperationsError("operation plan does not exist")
        if not plan.approved_for_review or plan.approver is None:
            raise PersonalOperationsError("only approved operation plans may project for review")
        return {
            "plan_id": plan.plan_id,
            "objective": plan.objective,
            "plan_sha256": plan.plan_sha256,
            "approved_for_review": True,
            "approver": plan.approver,
            "external_applied": plan.external_applied,
            "steps": tuple(
                {
                    "step_id": step.step_id,
                    "action": step.action,
                    "target": step.target,
                    "payload_sha256": step.payload_sha256,
                }
                for step in plan.steps
            ),
        }

    def apply_external(
        self,
        plan_id: str,
        *,
        context: ExternalExecutionContext | None = None,
        gateway: ToolGateway | None = None,
        authorization: AuthorizationEngine | None = None,
        grants: GrantPolicy | None = None,
        audit: AuditEngine | None = None,
        evidence: EvidenceStore | None = None,
    ) -> ExternalExecutionReceipt:
        plan = self._plans.get(plan_id)
        if plan is None:
            raise PersonalOperationsError("operation plan does not exist")
        if context is None or gateway is None or authorization is None or grants is None or audit is None or evidence is None:
            raise PersonalOperationsError("governed external execution dependencies are required")
        if self._execution_store is None:
            raise PersonalOperationsError("durable execution idempotency store is required")
        if not plan.approved_for_review or plan.approver is None:
            raise PersonalOperationsError("review approval is required before mutation approval")
        if not plan.steps or any(step.action not in _MUTATION_ACTIONS for step in plan.steps):
            raise PersonalOperationsError("external execution accepts mutation actions only")
        if not context.target_account.strip():
            raise PersonalOperationsError("target account is required")
        if context.access_request.action != _EXECUTION_ACTION:
            raise PersonalOperationsError("access request action does not authorize personal operations")
        if not context.access_request.high_risk or not context.access_request.approval_id:
            raise PersonalOperationsError("explicit independent mutation approval is required")
        if ("target_account", context.target_account) not in context.access_request.resource_attributes:
            raise PersonalOperationsError("target account is outside authorized resource scope")

        resource = f"{plan.plan_id}:{context.target_account}"
        details = {
            "plan_id": plan.plan_id,
            "principal_id": context.principal.principal_id,
            "tenant_id": context.principal.tenant_id,
            "target_account": context.target_account,
        }
        try:
            authorization.authorize(context.principal, context.access_request, context.now)
            grants.authorize(
                context.execution_grant,
                subject_id=context.principal.principal_id,
                action=_EXECUTION_ACTION,
                resource=resource,
                now=context.now,
            )
        except Exception:
            audit.record("personal_operations", "external.admission", "denied", details)
            raise

        audit.record("personal_operations", "external.admission", "success", details)
        receipts: list[ConnectorReceipt] = []
        for step in plan.steps:
            execution_key = hashlib.sha256(
                f"{plan.plan_sha256}:{step.step_id}:{context.target_account}".encode("utf-8")
            ).hexdigest()
            previous = self._execution_store.get(execution_key)
            if previous is not None:
                if previous.target_account != context.target_account:
                    raise PersonalOperationsError("idempotency receipt target mismatch")
                receipts.append(previous)
                continue
            try:
                receipt = self._dispatch_step(gateway, step, context.target_account, execution_key)
                if receipt.target_account != context.target_account:
                    raise PersonalOperationsError("connector receipt target account mismatch")
                artifact = evidence.put_artifact(_receipt_bytes(plan, step, receipt))
                evidence.append_provenance(execution_key, artifact, f"personal_operations.{step.action}")
                self._execution_store.put(execution_key, receipt)
                audit.record(
                    "personal_operations",
                    step.action,
                    "success",
                    {**details, "step_id": step.step_id, "provider_id": receipt.provider_id},
                )
                grants.record_side_effect(context.execution_grant, resource)
                receipts.append(receipt)
            except Exception:
                audit.record(
                    "personal_operations",
                    step.action,
                    "failure",
                    {**details, "step_id": step.step_id},
                )
                raise

        applied = replace(plan, external_applied=True)
        self._plans[plan_id] = applied
        return ExternalExecutionReceipt(plan.plan_id, context.target_account, tuple(receipts))

    @staticmethod
    def _dispatch_step(
        gateway: ToolGateway,
        step: OperationStep,
        target_account: str,
        execution_key: str,
    ) -> ConnectorReceipt:
        tool_name = f"personal_operations.{step.action}"
        kwargs: dict[str, str] = {
            "target_account": target_account,
            "idempotency_key": execution_key,
        }
        if step.action == "send_email":
            try:
                payload = json.loads(step.payload)
                subject = str(payload["subject"])
                body = str(payload["body"])
            except (KeyError, TypeError, json.JSONDecodeError) as error:
                raise PersonalOperationsError("send_email payload requires JSON subject and body") from error
            if not subject.strip() or not body.strip():
                raise PersonalOperationsError("send_email subject and body are required")
            kwargs.update({"recipient": step.target, "subject": subject, "body": body})
        elif step.action == "update_calendar_event":
            kwargs.update({"event_id": step.target, "payload": step.payload})
        else:
            kwargs["payload"] = step.payload
        result = gateway.dispatch(tool_name, **kwargs)
        if not isinstance(result, ConnectorReceipt):
            raise PersonalOperationsError("connector did not return a valid receipt")
        return result


def _receipt_bytes(plan: OperationPlan, step: OperationStep, receipt: ConnectorReceipt) -> bytes:
    return json.dumps(
        {
            "plan_id": plan.plan_id,
            "plan_sha256": plan.plan_sha256,
            "step_id": step.step_id,
            "action": step.action,
            "provider": receipt.provider,
            "provider_id": receipt.provider_id,
            "occurred_at": receipt.occurred_at.isoformat(),
            "target_account": receipt.target_account,
            "outcome": receipt.outcome,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _require_id(value: str, field: str) -> None:
    if not value or value != value.strip():
        raise PersonalOperationsError(f"{field} must be non-blank and trimmed")


def _require_text(value: str, field: str) -> None:
    if not value or not value.strip():
        raise PersonalOperationsError(f"{field} must be non-blank")

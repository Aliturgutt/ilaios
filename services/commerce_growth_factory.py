"""Bounded Commerce/Growth Factory with governed external execution."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol, TypedDict

from services.identity import AccessRequest, AuthorizationEngine, Principal
from src.core.audit_engine import AuditEngine
from src.core.evidence_chain import EvidenceChain, EvidenceRecord


class CommerceGrowthError(PermissionError):
    """Commerce/growth work violates a bounded governance or cost gate."""


_ALLOWED_CHANNELS = frozenset(
    {
        "content_draft",
        "email_draft",
        "sales_enablement",
        "social_draft",
    }
)
_EXECUTION_ACTION = "commerce_growth.execute"
_ALLOWED_PROVIDER_ACTIONS = {
    "content_draft": frozenset({"publish_content"}),
    "email_draft": frozenset({"send_email_campaign"}),
    "sales_enablement": frozenset({"sync_sales_asset"}),
    "social_draft": frozenset({"publish_social"}),
}


class GrowthToolGateway(Protocol):
    """Structural view of the canonical ToolGateway used by this factory."""

    def dispatch(self, tool_name: str, *args: Any, **kwargs: Any) -> Any: ...


class GrowthSourceProjection(TypedDict):
    source_id: str
    locator: str
    content_sha256: str


class GrowthReviewProjection(TypedDict):
    plan_id: str
    objective: str
    audience: str
    channels: tuple[str, ...]
    plan_sha256: str
    approved_for_review: bool
    approver: str
    paid_spend_cents: int
    sources: tuple[GrowthSourceProjection, ...]


@dataclass(frozen=True, slots=True)
class GrowthSource:
    source_id: str
    locator: str
    content_sha256: str
    trusted: bool


@dataclass(frozen=True, slots=True)
class GrowthPlan:
    plan_id: str
    objective: str
    audience: str
    channels: tuple[str, ...]
    source_ids: tuple[str, ...]
    paid_spend_cents: int
    plan_sha256: str
    approved_for_review: bool
    approver: str | None
    external_applied: bool = False


@dataclass(frozen=True, slots=True)
class GrowthExecutionRequest:
    execution_id: str
    provider: str
    provider_action: str
    target_account: str
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class GrowthExecutionReceipt:
    execution_id: str
    provider: str
    provider_action: str
    target_account: str
    provider_receipt_id: str
    provider_timestamp: str
    idempotency_key: str
    evidence_hash: str


class CommerceGrowthFactory:
    """Produce governed growth plans and execute approved zero-spend external actions."""

    def __init__(self) -> None:
        self._sources: dict[str, GrowthSource] = {}
        self._plans: dict[str, GrowthPlan] = {}
        self._executions: dict[str, GrowthExecutionReceipt] = {}
        self._used_idempotency_keys: set[str] = set()

    def register_source(
        self,
        source_id: str,
        *,
        locator: str,
        content: bytes,
        trusted: bool,
    ) -> GrowthSource:
        _require_id(source_id, "source_id")
        _require_text(locator, "locator")
        if not content:
            raise CommerceGrowthError("source content must not be empty")
        if source_id in self._sources:
            raise CommerceGrowthError("source_id already exists")
        source = GrowthSource(
            source_id=source_id,
            locator=locator,
            content_sha256=hashlib.sha256(content).hexdigest(),
            trusted=trusted,
        )
        self._sources[source_id] = source
        return source

    def propose(
        self,
        plan_id: str,
        *,
        objective: str,
        audience: str,
        channels: tuple[str, ...],
        source_ids: tuple[str, ...],
        paid_spend_cents: int = 0,
    ) -> GrowthPlan:
        _require_id(plan_id, "plan_id")
        _require_text(objective, "objective")
        _require_text(audience, "audience")
        if plan_id in self._plans:
            raise CommerceGrowthError("plan_id already exists")
        if paid_spend_cents != 0:
            raise CommerceGrowthError("paid spend is outside the bounded factory")
        normalized_channels = _unique_ids(channels, "channels")
        unsupported = sorted(set(normalized_channels) - _ALLOWED_CHANNELS)
        if unsupported:
            raise CommerceGrowthError(f"unsupported growth channels: {unsupported}")
        normalized_sources = _unique_ids(source_ids, "source_ids")
        missing = [source_id for source_id in normalized_sources if source_id not in self._sources]
        if missing:
            raise CommerceGrowthError(f"plan references unknown sources: {missing}")
        if any(not self._sources[source_id].trusted for source_id in normalized_sources):
            raise CommerceGrowthError("growth plan sources must be trusted")

        canonical = json.dumps(
            {
                "audience": audience.strip(),
                "channels": normalized_channels,
                "objective": objective.strip(),
                "paid_spend_cents": paid_spend_cents,
                "sources": tuple(
                    {
                        "content_sha256": self._sources[source_id].content_sha256,
                        "source_id": source_id,
                    }
                    for source_id in normalized_sources
                ),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        plan = GrowthPlan(
            plan_id=plan_id,
            objective=objective.strip(),
            audience=audience.strip(),
            channels=normalized_channels,
            source_ids=normalized_sources,
            paid_spend_cents=paid_spend_cents,
            plan_sha256=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            approved_for_review=False,
            approver=None,
        )
        self._plans[plan_id] = plan
        return plan

    def approve_for_review(self, plan_id: str, *, approver: str) -> GrowthPlan:
        _require_text(approver, "approver")
        plan = self._plans.get(plan_id)
        if plan is None:
            raise CommerceGrowthError("growth plan does not exist")
        if plan.approved_for_review:
            raise CommerceGrowthError("growth plan already approved for review")
        approved = GrowthPlan(
            plan_id=plan.plan_id,
            objective=plan.objective,
            audience=plan.audience,
            channels=plan.channels,
            source_ids=plan.source_ids,
            paid_spend_cents=plan.paid_spend_cents,
            plan_sha256=plan.plan_sha256,
            approved_for_review=True,
            approver=approver.strip(),
        )
        self._plans[plan_id] = approved
        return approved

    def review_projection(self, plan_id: str) -> GrowthReviewProjection:
        plan = self._plans.get(plan_id)
        if plan is None:
            raise CommerceGrowthError("growth plan does not exist")
        if not plan.approved_for_review or plan.approver is None:
            raise CommerceGrowthError("only approved growth plans may project for review")
        return {
            "plan_id": plan.plan_id,
            "objective": plan.objective,
            "audience": plan.audience,
            "channels": plan.channels,
            "plan_sha256": plan.plan_sha256,
            "approved_for_review": True,
            "approver": plan.approver,
            "paid_spend_cents": plan.paid_spend_cents,
            "sources": tuple(
                {
                    "source_id": source_id,
                    "locator": self._sources[source_id].locator,
                    "content_sha256": self._sources[source_id].content_sha256,
                }
                for source_id in plan.source_ids
            ),
        }

    def apply_external(
        self,
        plan_id: str,
        *,
        request: GrowthExecutionRequest | None = None,
        principal: Principal | None = None,
        authorization: AuthorizationEngine | None = None,
        approval_id: str | None = None,
        tool_gateway: GrowthToolGateway | None = None,
        audit: AuditEngine | None = None,
        evidence: EvidenceChain | None = None,
        now: datetime | None = None,
    ) -> GrowthExecutionReceipt:
        plan = self._plans.get(plan_id)
        if plan is None:
            raise CommerceGrowthError("growth plan does not exist")
        if not plan.approved_for_review or plan.approver is None:
            raise CommerceGrowthError("review approval is required before external execution")
        if plan.external_applied:
            raise CommerceGrowthError("growth plan external action was already applied")
        if plan.paid_spend_cents != 0:
            raise CommerceGrowthError("paid external execution is not enabled")
        if (
            request is None
            or principal is None
            or authorization is None
            or tool_gateway is None
            or audit is None
            or evidence is None
        ):
            raise CommerceGrowthError(
                "external execution requires request, identity, authorization, Tool Gateway, audit and evidence"
            )
        self._validate_execution_request(plan, request)
        if request.execution_id in self._executions:
            raise CommerceGrowthError("execution_id already exists")
        if request.idempotency_key in self._used_idempotency_keys:
            raise CommerceGrowthError("idempotency_key already used")

        executed_at = now or datetime.now(timezone.utc)
        if executed_at.tzinfo is None or executed_at.utcoffset() != timezone.utc.utcoffset(executed_at):
            raise CommerceGrowthError("execution time must be timezone-aware UTC")

        authorization.authorize(
            principal,
            AccessRequest(
                tenant_id=principal.tenant_id,
                resource_tenant_id=principal.tenant_id,
                action=_EXECUTION_ACTION,
                privileged=True,
                high_risk=True,
                approval_id=approval_id,
            ),
            executed_at,
        )

        payload = {
            "execution_id": request.execution_id,
            "plan_id": plan.plan_id,
            "plan_sha256": plan.plan_sha256,
            "provider": request.provider,
            "provider_action": request.provider_action,
            "target_account": request.target_account,
            "idempotency_key": request.idempotency_key,
            "tenant_id": principal.tenant_id,
            "principal_id": principal.principal_id,
        }
        try:
            provider_result = tool_gateway.dispatch(_EXECUTION_ACTION, payload=payload)
            receipt = self._validate_provider_result(request, provider_result)
        except Exception as exc:
            audit.record(
                "commerce_growth_factory",
                _EXECUTION_ACTION,
                "failure",
                {
                    "execution_id": request.execution_id,
                    "plan_id": plan.plan_id,
                    "provider": request.provider,
                    "error_type": type(exc).__name__,
                },
                timestamp=executed_at,
            )
            raise CommerceGrowthError("external provider execution failed closed") from exc

        evidence_payload = json.dumps(
            {
                "execution_id": request.execution_id,
                "idempotency_key": request.idempotency_key,
                "plan_id": plan.plan_id,
                "plan_sha256": plan.plan_sha256,
                "provider": request.provider,
                "provider_action": request.provider_action,
                "provider_receipt_id": receipt["provider_receipt_id"],
                "provider_timestamp": receipt["provider_timestamp"],
                "target_account": request.target_account,
                "tenant_id": principal.tenant_id,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        data_hash = hashlib.sha256(evidence_payload.encode("utf-8")).hexdigest()
        existing_records = evidence.get_records()
        evidence.add_record(
            EvidenceRecord(
                timestamp=executed_at,
                source="commerce_growth_factory.external_execution",
                data_hash=data_hash,
                prev_hash=existing_records[-1].chain_hash if existing_records else None,
            )
        )
        execution_receipt = GrowthExecutionReceipt(
            execution_id=request.execution_id,
            provider=request.provider,
            provider_action=request.provider_action,
            target_account=request.target_account,
            provider_receipt_id=receipt["provider_receipt_id"],
            provider_timestamp=receipt["provider_timestamp"],
            idempotency_key=request.idempotency_key,
            evidence_hash=data_hash,
        )
        self._executions[request.execution_id] = execution_receipt
        self._used_idempotency_keys.add(request.idempotency_key)
        self._plans[plan_id] = GrowthPlan(
            plan_id=plan.plan_id,
            objective=plan.objective,
            audience=plan.audience,
            channels=plan.channels,
            source_ids=plan.source_ids,
            paid_spend_cents=plan.paid_spend_cents,
            plan_sha256=plan.plan_sha256,
            approved_for_review=plan.approved_for_review,
            approver=plan.approver,
            external_applied=True,
        )
        audit.record(
            "commerce_growth_factory",
            _EXECUTION_ACTION,
            "success",
            {
                "execution_id": request.execution_id,
                "plan_id": plan.plan_id,
                "provider": request.provider,
                "provider_receipt_id": receipt["provider_receipt_id"],
            },
            timestamp=executed_at,
        )
        return execution_receipt

    def execution_receipt(self, execution_id: str) -> GrowthExecutionReceipt:
        receipt = self._executions.get(execution_id)
        if receipt is None:
            raise CommerceGrowthError("execution receipt does not exist")
        return receipt

    def _validate_execution_request(
        self, plan: GrowthPlan, request: GrowthExecutionRequest
    ) -> None:
        _require_id(request.execution_id, "execution_id")
        _require_text(request.provider, "provider")
        _require_text(request.provider_action, "provider_action")
        _require_text(request.target_account, "target_account")
        _require_id(request.idempotency_key, "idempotency_key")
        allowed_actions = frozenset().union(
            *(_ALLOWED_PROVIDER_ACTIONS[channel] for channel in plan.channels)
        )
        if request.provider_action not in allowed_actions:
            raise CommerceGrowthError("provider action is not allowed by the approved plan channels")

    @staticmethod
    def _validate_provider_result(
        request: GrowthExecutionRequest, provider_result: Any
    ) -> Mapping[str, str]:
        if not isinstance(provider_result, Mapping):
            raise CommerceGrowthError("provider result must be a mapping")
        required = (
            "outcome",
            "provider_receipt_id",
            "provider_timestamp",
            "target_account",
            "idempotency_key",
        )
        if any(
            not isinstance(provider_result.get(field), str)
            or not str(provider_result.get(field)).strip()
            for field in required
        ):
            raise CommerceGrowthError("provider result is missing required receipt fields")
        if provider_result["outcome"] != "success":
            raise CommerceGrowthError("provider did not report successful execution")
        if provider_result["target_account"] != request.target_account:
            raise CommerceGrowthError("provider receipt target account mismatch")
        if provider_result["idempotency_key"] != request.idempotency_key:
            raise CommerceGrowthError("provider receipt idempotency key mismatch")
        return provider_result


def _require_id(value: str, field: str) -> None:
    if not value or value != value.strip():
        raise CommerceGrowthError(f"{field} must be non-blank and trimmed")


def _require_text(value: str, field: str) -> None:
    if not value or not value.strip():
        raise CommerceGrowthError(f"{field} must be non-blank")


def _unique_ids(values: tuple[str, ...], field: str) -> tuple[str, ...]:
    if not values:
        raise CommerceGrowthError(f"{field} must not be empty")
    if any(not item or item != item.strip() for item in values):
        raise CommerceGrowthError(f"{field} must contain trimmed values")
    if len(values) != len(set(values)):
        raise CommerceGrowthError(f"{field} must not contain duplicates")
    return values

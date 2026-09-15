"""Durable governed Web publish orchestration built on existing delivery adapters.

This module is not a second deployment authority. It persists user-facing publish
state and composes the existing ``web.deployment-receipt.v1`` provider contract.
Authorization, approval, budget and credential truth are supplied by the canonical
ILAIOS governance path and are never minted here.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Mapping, Protocol

from .web_delivery import WebDeploymentError, WebDeploymentReceipt, tree_sha256


class WebPublishError(RuntimeError):
    """Raised when publish state or evidence cannot be proven."""


class WebPublishState(StrEnum):
    DRAFT = "DRAFT"
    PREVIEW_READY = "PREVIEW_READY"
    PUBLISH_REQUESTED = "PUBLISH_REQUESTED"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    DEPLOYING = "DEPLOYING"
    VERIFYING = "VERIFYING"
    LIVE = "LIVE"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


_ALLOWED_TRANSITIONS: Mapping[WebPublishState, frozenset[WebPublishState]] = {
    WebPublishState.DRAFT: frozenset({WebPublishState.PREVIEW_READY, WebPublishState.FAILED}),
    WebPublishState.PREVIEW_READY: frozenset(
        {WebPublishState.PUBLISH_REQUESTED, WebPublishState.FAILED}
    ),
    WebPublishState.PUBLISH_REQUESTED: frozenset(
        {WebPublishState.WAITING_APPROVAL, WebPublishState.DEPLOYING, WebPublishState.FAILED}
    ),
    WebPublishState.WAITING_APPROVAL: frozenset(
        {WebPublishState.DEPLOYING, WebPublishState.FAILED}
    ),
    WebPublishState.DEPLOYING: frozenset({WebPublishState.VERIFYING, WebPublishState.FAILED}),
    WebPublishState.VERIFYING: frozenset({WebPublishState.LIVE, WebPublishState.FAILED}),
    WebPublishState.LIVE: frozenset(
        {WebPublishState.PREVIEW_READY, WebPublishState.ROLLED_BACK, WebPublishState.FAILED}
    ),
    WebPublishState.FAILED: frozenset({WebPublishState.PREVIEW_READY}),
    WebPublishState.ROLLED_BACK: frozenset({WebPublishState.PREVIEW_READY}),
}


@dataclass(frozen=True, slots=True)
class AcceptedWebArtifact:
    site_id: str
    tenant_id: str
    project_root: Path
    source_commit_sha: str
    artifact_sha256: str
    acceptance_proven: bool

    def validate(self) -> None:
        if not self.site_id.strip() or not self.tenant_id.strip():
            raise WebPublishError("site and tenant identity are required")
        if self.acceptance_proven is not True:
            raise WebPublishError("Web artifact acceptance is not proven")
        if not self.project_root.is_dir():
            raise WebPublishError("accepted Web source project is missing")
        if len(self.source_commit_sha) != 40 or any(
            character not in "0123456789abcdef" for character in self.source_commit_sha
        ):
            raise WebPublishError("accepted Web source commit SHA is malformed")
        if len(self.artifact_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.artifact_sha256
        ):
            raise WebPublishError("accepted Web artifact digest is malformed")
        if tree_sha256(self.project_root) != self.artifact_sha256:
            raise WebPublishError("accepted Web artifact digest does not match source project")


@dataclass(frozen=True, slots=True)
class DNSRecordInstruction:
    record_type: str
    name: str
    value: str
    purpose: str


@dataclass(frozen=True, slots=True)
class ManualDomainPlan:
    domain: str
    target_host: str
    verification_token: str
    records: tuple[DNSRecordInstruction, ...]


class WebPublicDeploymentAdapter(Protocol):
    provider_id: str

    def preview(
        self,
        project_root: Path,
        *,
        source_commit_sha: str,
        expected_artifact_sha256: str | None,
        preview_authorization_proven: bool,
        budget_proven: bool,
    ) -> WebDeploymentReceipt: ...

    def deploy(
        self,
        project_root: Path,
        *,
        source_commit_sha: str,
        expected_artifact_sha256: str | None,
        rollback_reference: str | None,
        authorization_proven: bool,
        budget_proven: bool,
    ) -> WebDeploymentReceipt: ...

    def rollback(
        self,
        deployment_id: str,
        *,
        source_commit_sha: str,
        expected_artifact_sha256: str,
        replaced_deployment_id: str | None,
        authorization_proven: bool,
        budget_proven: bool,
    ) -> WebDeploymentReceipt: ...


class WebSmokeVerifier(Protocol):
    def verify(self, url: str) -> bool: ...


class DNSResolver(Protocol):
    def cname(self, host: str) -> tuple[str, ...]: ...

    def txt(self, host: str) -> tuple[str, ...]: ...


class WebPublishStore:
    """Tenant-scoped durable publish history; not an authority or evidence replacement."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS web_publish_history ("
                "sequence INTEGER PRIMARY KEY AUTOINCREMENT, "
                "tenant_id TEXT NOT NULL, site_id TEXT NOT NULL, state TEXT NOT NULL, "
                "receipt_json TEXT, reason TEXT NOT NULL DEFAULT '')"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS web_domain_bindings ("
                "tenant_id TEXT NOT NULL, site_id TEXT NOT NULL, domain TEXT NOT NULL, "
                "target_host TEXT NOT NULL, verification_token TEXT NOT NULL, "
                "status TEXT NOT NULL, PRIMARY KEY (tenant_id, site_id, domain))"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def current_state(self, tenant_id: str, site_id: str) -> WebPublishState | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT state FROM web_publish_history WHERE tenant_id=? AND site_id=? "
                "ORDER BY sequence DESC LIMIT 1",
                (tenant_id, site_id),
            ).fetchone()
        return None if row is None else WebPublishState(str(row["state"]))

    def ensure_draft(self, tenant_id: str, site_id: str) -> None:
        if self.current_state(tenant_id, site_id) is None:
            self._append(tenant_id, site_id, WebPublishState.DRAFT, None, "")

    def transition(
        self,
        tenant_id: str,
        site_id: str,
        state: WebPublishState,
        *,
        receipt: WebDeploymentReceipt | None = None,
        reason: str = "",
    ) -> None:
        current = self.current_state(tenant_id, site_id)
        if current is None:
            if state is not WebPublishState.DRAFT:
                raise WebPublishError("publish history must begin at DRAFT")
        elif state not in _ALLOWED_TRANSITIONS[current]:
            raise WebPublishError(f"invalid Web publish transition: {current} -> {state}")
        self._append(tenant_id, site_id, state, receipt, reason)

    def _append(
        self,
        tenant_id: str,
        site_id: str,
        state: WebPublishState,
        receipt: WebDeploymentReceipt | None,
        reason: str,
    ) -> None:
        payload = None if receipt is None else json.dumps(receipt.to_dict(), sort_keys=True)
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO web_publish_history "
                "(tenant_id, site_id, state, receipt_json, reason) VALUES (?, ?, ?, ?, ?)",
                (tenant_id, site_id, state.value, payload, reason),
            )

    def history(self, tenant_id: str, site_id: str) -> tuple[dict[str, object], ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT sequence, state, receipt_json, reason FROM web_publish_history "
                "WHERE tenant_id=? AND site_id=? ORDER BY sequence",
                (tenant_id, site_id),
            ).fetchall()
        return tuple(
            {
                "sequence": int(row["sequence"]),
                "state": str(row["state"]),
                "receipt": None
                if row["receipt_json"] is None
                else json.loads(str(row["receipt_json"])),
                "reason": str(row["reason"]),
            }
            for row in rows
        )

    def save_domain_plan(self, tenant_id: str, site_id: str, plan: ManualDomainPlan) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO web_domain_bindings "
                "(tenant_id, site_id, domain, target_host, verification_token, status) "
                "VALUES (?, ?, ?, ?, ?, 'PENDING_DNS')",
                (
                    tenant_id,
                    site_id,
                    plan.domain,
                    plan.target_host,
                    plan.verification_token,
                ),
            )

    def mark_domain_verified(self, tenant_id: str, site_id: str, domain: str) -> None:
        with self._connect() as connection:
            changed = connection.execute(
                "UPDATE web_domain_bindings SET status='DNS_VERIFIED' "
                "WHERE tenant_id=? AND site_id=? AND domain=?",
                (tenant_id, site_id, domain),
            ).rowcount
        if changed != 1:
            raise WebPublishError("domain binding does not exist")


class WebPublishCoordinator:
    """Compose accepted Web artifacts with an existing governed provider adapter."""

    def __init__(
        self,
        store: WebPublishStore,
        deployment: WebPublicDeploymentAdapter,
        verifier: WebSmokeVerifier,
    ) -> None:
        self._store = store
        self._deployment = deployment
        self._verifier = verifier

    def preview(
        self,
        artifact: AcceptedWebArtifact,
        *,
        preview_authorization_proven: bool,
        budget_proven: bool,
    ) -> WebDeploymentReceipt:
        artifact.validate()
        self._store.ensure_draft(artifact.tenant_id, artifact.site_id)
        current = self._store.current_state(artifact.tenant_id, artifact.site_id)
        if current not in {
            WebPublishState.DRAFT,
            WebPublishState.LIVE,
            WebPublishState.FAILED,
            WebPublishState.ROLLED_BACK,
        }:
            raise WebPublishError("preview cannot start from the current publish state")
        receipt = self._deployment.preview(
            artifact.project_root,
            source_commit_sha=artifact.source_commit_sha,
            expected_artifact_sha256=artifact.artifact_sha256,
            preview_authorization_proven=preview_authorization_proven,
            budget_proven=budget_proven,
        )
        if receipt.public_production_proven:
            raise WebPublishError("preview receipt cannot claim public production")
        if not self._verifier.verify(receipt.live_url):
            self._store.transition(
                artifact.tenant_id,
                artifact.site_id,
                WebPublishState.FAILED,
                receipt=receipt,
                reason="preview smoke verification failed",
            )
            raise WebPublishError("preview smoke verification failed")
        self._store.transition(
            artifact.tenant_id,
            artifact.site_id,
            WebPublishState.PREVIEW_READY,
            receipt=receipt,
        )
        return receipt

    def request_publish(self, artifact: AcceptedWebArtifact, *, human_approval_required: bool) -> None:
        artifact.validate()
        if self._store.current_state(artifact.tenant_id, artifact.site_id) is not WebPublishState.PREVIEW_READY:
            raise WebPublishError("publish requires a verified preview")
        self._store.transition(
            artifact.tenant_id,
            artifact.site_id,
            WebPublishState.PUBLISH_REQUESTED,
        )
        if human_approval_required:
            self._store.transition(
                artifact.tenant_id,
                artifact.site_id,
                WebPublishState.WAITING_APPROVAL,
            )

    def publish(
        self,
        artifact: AcceptedWebArtifact,
        *,
        authorization_proven: bool,
        approval_proven: bool,
        human_approval_required: bool,
        budget_proven: bool,
    ) -> WebDeploymentReceipt:
        artifact.validate()
        current = self._store.current_state(artifact.tenant_id, artifact.site_id)
        expected = (
            WebPublishState.WAITING_APPROVAL
            if human_approval_required
            else WebPublishState.PUBLISH_REQUESTED
        )
        if current is not expected:
            raise WebPublishError("publish request state does not match approval policy")
        if human_approval_required and approval_proven is not True:
            raise WebPublishError("required production approval is not proven")
        if authorization_proven is not True or budget_proven is not True:
            raise WebPublishError("production deployment authority or budget is not proven")
        self._store.transition(
            artifact.tenant_id,
            artifact.site_id,
            WebPublishState.DEPLOYING,
        )
        receipt = self._deployment.deploy(
            artifact.project_root,
            source_commit_sha=artifact.source_commit_sha,
            expected_artifact_sha256=artifact.artifact_sha256,
            rollback_reference=None,
            authorization_proven=authorization_proven,
            budget_proven=budget_proven,
        )
        self._store.transition(
            artifact.tenant_id,
            artifact.site_id,
            WebPublishState.VERIFYING,
            receipt=receipt,
        )
        if receipt.public_production_proven is not True or not self._verifier.verify(
            receipt.live_url
        ):
            self._store.transition(
                artifact.tenant_id,
                artifact.site_id,
                WebPublishState.FAILED,
                receipt=receipt,
                reason="public production verification failed",
            )
            raise WebPublishError("public production verification failed")
        self._store.transition(
            artifact.tenant_id,
            artifact.site_id,
            WebPublishState.LIVE,
            receipt=receipt,
        )
        return receipt


def manual_domain_plan(
    domain: str,
    *,
    target_host: str,
    verification_token: str,
) -> ManualDomainPlan:
    normalized = _normalize_domain(domain)
    target = _normalize_domain(target_host)
    token = verification_token.strip()
    if len(token) < 16 or not re.fullmatch(r"[A-Za-z0-9_-]+", token):
        raise WebPublishError("domain verification token is invalid")
    host = "www" if normalized.startswith("www.") else "@"
    return ManualDomainPlan(
        domain=normalized,
        target_host=target,
        verification_token=token,
        records=(
            DNSRecordInstruction("CNAME", host, target, "route domain to ILAIOS hosting"),
            DNSRecordInstruction(
                "TXT",
                "_ilaios-domain-verification",
                token,
                "prove domain control",
            ),
        ),
    )


def verify_manual_domain(plan: ManualDomainPlan, resolver: DNSResolver) -> None:
    cname_host = plan.domain if plan.domain.startswith("www.") else plan.domain
    cname_values = {_normalize_domain(value) for value in resolver.cname(cname_host)}
    if plan.target_host not in cname_values:
        raise WebPublishError("custom domain CNAME is not verified")
    txt_host = f"_ilaios-domain-verification.{plan.domain}"
    if plan.verification_token not in set(resolver.txt(txt_host)):
        raise WebPublishError("custom domain ownership TXT is not verified")


def _normalize_domain(value: str) -> str:
    normalized = value.strip().lower().rstrip(".")
    if not normalized or len(normalized) > 253 or "/" in normalized or ":" in normalized:
        raise WebPublishError("domain name is invalid")
    labels = normalized.split(".")
    if len(labels) < 2 or any(
        not label
        or len(label) > 63
        or label.startswith("-")
        or label.endswith("-")
        or re.fullmatch(r"[a-z0-9-]+", label) is None
        for label in labels
    ):
        raise WebPublishError("domain name is invalid")
    return normalized


__all__ = [
    "AcceptedWebArtifact",
    "DNSRecordInstruction",
    "DNSResolver",
    "ManualDomainPlan",
    "WebPublishCoordinator",
    "WebPublishError",
    "WebPublishState",
    "WebPublishStore",
    "WebSmokeVerifier",
    "manual_domain_plan",
    "verify_manual_domain",
]

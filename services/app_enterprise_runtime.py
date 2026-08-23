"""Stage-3 enterprise App Factory runtime binding over incumbent backend services.

This module deliberately does not create a second backend, identity engine, policy
engine, approval engine, tool gateway, audit authority, evidence authority, or
realtime authority. It binds the Stage-2 ProductSpec/Domain/Auth contracts to the
already implemented ``WebAppCrudRuntime`` persistence boundary and the existing
``WebAppRealtimeRuntime`` authenticated event projection so Web, Windows, Android
and iOS clients can converge on one governed application backend contract.

This slice proves deterministic lineage plus entity/permission binding for
persistent create/read/list/update/delete operations and authenticated replayable
realtime projection. API transport, files, integrations and commerce remain
separate dependency-ordered slices.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from services.app_auth_rbac_plan import AuthRbacPlan
from services.app_domain_model import DomainModelPlan
from services.app_product_spec import ProductSpec
from services.identity import Principal
from services.web_app_auth_contract import WebAppAuthContract
from services.web_app_crud_runtime import CrudPage, CrudRecord, WebAppCrudRuntime
from services.web_app_realtime_runtime import (
    RealtimeBatch,
    RealtimeEvent,
    RealtimeEventType,
    WebAppRealtimeRuntime,
)

EnterpriseOperation = Literal["create", "read", "list", "update", "delete"]


class AppEnterpriseRuntimeError(ValueError):
    """Stage-3 runtime binding is incomplete, stale, or authority-unsafe."""


@dataclass(frozen=True, slots=True)
class AppEnterpriseRuntimeBinding:
    project_id: str
    spec_sha256: str
    domain_model_sha256: str
    auth_rbac_plan_sha256: str
    entities: tuple[str, ...]
    operations: tuple[EnterpriseOperation, ...]
    backend_authority: Literal["services.web_app_crud_runtime.WebAppCrudRuntime"]
    realtime_authority: Literal["services.web_app_realtime_runtime.WebAppRealtimeRuntime"]
    authorization_authority: Literal["services.identity.AuthorizationEngine"]
    implementation_authority: Literal["software-factory"]
    direct_database_authority: Literal[False]
    direct_realtime_mutation_authority: Literal[False]
    binding_sha256: str


def bind_enterprise_runtime(
    *,
    spec: ProductSpec,
    domain_model: DomainModelPlan,
    auth_rbac: AuthRbacPlan,
    backend_contract: WebAppAuthContract,
) -> AppEnterpriseRuntimeBinding:
    """Bind immutable Stage-2 contracts to incumbent CRUD and realtime runtimes."""
    if domain_model.project_id != spec.project_id or domain_model.spec_sha256 != spec.spec_sha256:
        raise AppEnterpriseRuntimeError("domain model is not bound to the supplied ProductSpec")
    if auth_rbac.project_id != spec.project_id or auth_rbac.spec_sha256 != spec.spec_sha256:
        raise AppEnterpriseRuntimeError("auth/RBAC plan is not bound to the supplied ProductSpec")
    if auth_rbac.architecture_plan_sha256 != domain_model.architecture_plan_sha256:
        raise AppEnterpriseRuntimeError("domain and auth/RBAC plans do not share one architecture")
    if not auth_rbac.authentication_required or not auth_rbac.authorization_required:
        raise AppEnterpriseRuntimeError("enterprise persistence runtime requires authenticated RBAC")
    if not auth_rbac.default_deny or not auth_rbac.server_authoritative:
        raise AppEnterpriseRuntimeError("enterprise runtime requires server-authoritative default deny")
    if backend_contract.project_id != spec.project_id or backend_contract.spec_sha256 != spec.spec_sha256:
        raise AppEnterpriseRuntimeError("CRUD backend contract is not bound to the supplied ProductSpec")
    if not backend_contract.authentication_required or not backend_contract.default_deny:
        raise AppEnterpriseRuntimeError("CRUD backend contract must require authentication and default deny")
    if backend_contract.authorization_authority != "services.identity.AuthorizationEngine":
        raise AppEnterpriseRuntimeError("CRUD backend must retain canonical authorization authority")

    entities = tuple(entity.entity_id for entity in domain_model.entities)
    if not entities:
        raise AppEnterpriseRuntimeError("enterprise persistence runtime requires domain entities")
    backend_permissions = frozenset(permission.permission for permission in backend_contract.permissions)
    planned_permissions = frozenset(grant.permission for role in auth_rbac.roles for grant in role.grants)
    for entity in entities:
        for operation in ("create", "read", "update", "delete"):
            permission = f"resource.{entity}.{operation}"
            if permission not in planned_permissions:
                raise AppEnterpriseRuntimeError(
                    f"auth/RBAC plan is missing runtime permission {permission}"
                )
            if permission not in backend_permissions:
                raise AppEnterpriseRuntimeError(
                    f"CRUD backend contract is missing runtime permission {permission}"
                )

    operations: tuple[EnterpriseOperation, ...] = ("create", "read", "list", "update", "delete")
    canonical: dict[str, object] = {
        "auth_rbac_plan_sha256": auth_rbac.plan_sha256,
        "authorization_authority": "services.identity.AuthorizationEngine",
        "backend_authority": "services.web_app_crud_runtime.WebAppCrudRuntime",
        "direct_database_authority": False,
        "direct_realtime_mutation_authority": False,
        "domain_model_sha256": domain_model.model_sha256,
        "entities": list(entities),
        "implementation_authority": "software-factory",
        "operations": list(operations),
        "project_id": spec.project_id,
        "realtime_authority": "services.web_app_realtime_runtime.WebAppRealtimeRuntime",
        "spec_sha256": spec.spec_sha256,
    }
    return AppEnterpriseRuntimeBinding(
        project_id=spec.project_id,
        spec_sha256=spec.spec_sha256,
        domain_model_sha256=domain_model.model_sha256,
        auth_rbac_plan_sha256=auth_rbac.plan_sha256,
        entities=entities,
        operations=operations,
        backend_authority="services.web_app_crud_runtime.WebAppCrudRuntime",
        realtime_authority="services.web_app_realtime_runtime.WebAppRealtimeRuntime",
        authorization_authority="services.identity.AuthorizationEngine",
        implementation_authority="software-factory",
        direct_database_authority=False,
        direct_realtime_mutation_authority=False,
        binding_sha256=_sha256_json(canonical),
    )


class AppEnterpriseRuntime:
    """Cross-platform adapter over existing governed CRUD and realtime runtimes."""

    def __init__(
        self,
        binding: AppEnterpriseRuntimeBinding,
        backend: WebAppCrudRuntime,
        realtime: WebAppRealtimeRuntime,
    ) -> None:
        self._binding = binding
        self._backend = backend
        self._realtime = realtime
        self._entities = frozenset(binding.entities)

    @property
    def binding(self) -> AppEnterpriseRuntimeBinding:
        return self._binding

    def create(self, *, principal: Principal, entity: str, resource_id: str, payload: dict[str, object], idempotency_key: str, now: datetime) -> CrudRecord:
        self._require_entity(entity)
        return self._backend.create(principal=principal, resource_type=entity, resource_id=resource_id, payload=payload, idempotency_key=idempotency_key, now=now)

    def read(self, *, principal: Principal, entity: str, resource_id: str, now: datetime) -> CrudRecord:
        self._require_entity(entity)
        return self._backend.read(principal=principal, resource_type=entity, resource_id=resource_id, now=now)

    def list(self, *, principal: Principal, entity: str, now: datetime, offset: int = 0, limit: int = 50) -> CrudPage:
        self._require_entity(entity)
        return self._backend.list(principal=principal, resource_type=entity, now=now, offset=offset, limit=limit)

    def update(self, *, principal: Principal, entity: str, resource_id: str, payload: dict[str, object], expected_version: int, idempotency_key: str, now: datetime) -> CrudRecord:
        self._require_entity(entity)
        return self._backend.update(principal=principal, resource_type=entity, resource_id=resource_id, payload=payload, expected_version=expected_version, idempotency_key=idempotency_key, now=now)

    def delete(self, *, principal: Principal, entity: str, resource_id: str, expected_version: int, now: datetime) -> None:
        self._require_entity(entity)
        self._backend.delete(principal=principal, resource_type=entity, resource_id=resource_id, expected_version=expected_version, now=now)

    def publish_realtime(
        self,
        *,
        principal: Principal,
        entity: str,
        resource_id: str,
        event_type: RealtimeEventType,
        payload: dict[str, object],
        now: datetime,
        resource_version: int | None = None,
    ) -> RealtimeEvent:
        """Publish through the incumbent authenticated realtime projection only."""
        self._require_entity(entity)
        return self._realtime.publish(
            principal=principal,
            resource_type=entity,
            resource_id=resource_id,
            event_type=event_type,
            payload=payload,
            now=now,
            resource_version=resource_version,
        )

    def subscribe_realtime(
        self,
        *,
        principal: Principal,
        entity: str,
        now: datetime,
        after_sequence: int = 0,
        resource_id: str | None = None,
        limit: int | None = None,
    ) -> RealtimeBatch:
        """Replay authorized entity events without introducing transport authority."""
        self._require_entity(entity)
        return self._realtime.subscribe(
            principal=principal,
            resource_type=entity,
            now=now,
            after_sequence=after_sequence,
            resource_id=resource_id,
            limit=limit,
        )

    def _require_entity(self, entity: str) -> None:
        if entity not in self._entities:
            raise AppEnterpriseRuntimeError("entity is not admitted by the bound DomainModelPlan")


def _sha256_json(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

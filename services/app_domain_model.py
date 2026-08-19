"""Deterministic Stage-2 enterprise application domain-model contracts.

This module is specification/planning only. It does not create database schemas,
run migrations, mutate source, access credentials, deploy, sign, submit, publish,
or create a second runtime/core. Real implementation remains downstream through
the canonical Software Factory and governance/evidence boundaries.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Literal

from services.app_architecture_plan import ApplicationArchitecturePlan
from services.app_product_spec import ProductSpec


DomainFieldType = Literal[
    "uuid", "string", "integer", "boolean", "datetime", "decimal", "json", "bytes"
]
RelationshipKind = Literal["one-to-one", "one-to-many", "many-to-one", "many-to-many"]


class AppDomainModelError(ValueError):
    """Domain-model input is invalid, ambiguous, or violates enterprise invariants."""


@dataclass(frozen=True, slots=True)
class DomainField:
    name: str
    field_type: DomainFieldType
    nullable: bool = False
    unique: bool = False
    indexed: bool = False


@dataclass(frozen=True, slots=True)
class DomainRelationship:
    name: str
    target_entity: str
    kind: RelationshipKind
    nullable: bool = False


@dataclass(frozen=True, slots=True)
class DomainEntity:
    entity_id: str
    tenant_owned: bool
    fields: tuple[DomainField, ...]
    relationships: tuple[DomainRelationship, ...] = ()
    indexes: tuple[tuple[str, ...], ...] = ()
    lifecycle_states: tuple[str, ...] = ("active",)
    versioned: bool = False
    audit_required: bool = True


@dataclass(frozen=True, slots=True)
class DomainModelPlan:
    project_id: str
    spec_sha256: str
    architecture_plan_sha256: str
    entities: tuple[DomainEntity, ...]
    tenant_isolation_required: bool
    stable_ids_required: Literal[True]
    timestamps_required: Literal[True]
    implementation_authority: Literal["software-factory"]
    direct_database_mutation_allowed: Literal[False]
    model_sha256: str


def build_domain_model(
    *,
    spec: ProductSpec,
    architecture: ApplicationArchitecturePlan,
    entities: tuple[DomainEntity, ...],
) -> DomainModelPlan:
    """Validate and bind an immutable product domain model without implementation authority."""
    if architecture.project_id != spec.project_id or architecture.spec_sha256 != spec.spec_sha256:
        raise AppDomainModelError("architecture plan must be bound to the supplied ProductSpec")
    if architecture.persistence_mode == "relational" and not entities:
        raise AppDomainModelError("relational architecture requires at least one domain entity")

    entity_ids = tuple(entity.entity_id for entity in entities)
    _require_unique_tokens(entity_ids, "entity_id")
    known_entities = frozenset(entity_ids)

    for entity in entities:
        _validate_entity(entity, known_entities=known_entities)

    tenant_isolation_required = any(entity.tenant_owned for entity in entities)
    canonical: dict[str, object] = {
        "architecture_plan_sha256": architecture.plan_sha256,
        "direct_database_mutation_allowed": False,
        "entities": [_entity_payload(entity) for entity in entities],
        "implementation_authority": "software-factory",
        "project_id": spec.project_id,
        "spec_sha256": spec.spec_sha256,
        "stable_ids_required": True,
        "tenant_isolation_required": tenant_isolation_required,
        "timestamps_required": True,
    }
    return DomainModelPlan(
        project_id=spec.project_id,
        spec_sha256=spec.spec_sha256,
        architecture_plan_sha256=architecture.plan_sha256,
        entities=entities,
        tenant_isolation_required=tenant_isolation_required,
        stable_ids_required=True,
        timestamps_required=True,
        implementation_authority="software-factory",
        direct_database_mutation_allowed=False,
        model_sha256=_sha256_json(canonical),
    )


def _validate_entity(entity: DomainEntity, *, known_entities: frozenset[str]) -> None:
    _require_token(entity.entity_id, "entity_id")
    if not entity.fields:
        raise AppDomainModelError(f"entity {entity.entity_id} requires fields")

    field_names = tuple(field.name for field in entity.fields)
    _require_unique_tokens(field_names, f"{entity.entity_id}.fields")
    fields_by_name = {field.name: field for field in entity.fields}

    stable_id = fields_by_name.get("id")
    if stable_id is None or stable_id.field_type != "uuid":
        raise AppDomainModelError(f"entity {entity.entity_id} requires uuid id field")
    if stable_id.nullable or not stable_id.unique:
        raise AppDomainModelError(
            f"entity {entity.entity_id} id must be non-null and unique"
        )

    for timestamp in ("created_at", "updated_at"):
        field = fields_by_name.get(timestamp)
        if field is None or field.field_type != "datetime" or field.nullable:
            raise AppDomainModelError(
                f"entity {entity.entity_id} requires non-null datetime {timestamp}"
            )

    if entity.tenant_owned:
        tenant_field = fields_by_name.get("tenant_id")
        if (
            tenant_field is None
            or tenant_field.field_type != "uuid"
            or tenant_field.nullable
            or not tenant_field.indexed
        ):
            raise AppDomainModelError(
                f"tenant-owned entity {entity.entity_id} requires indexed uuid tenant_id"
            )

    if entity.versioned:
        version_field = fields_by_name.get("version")
        if (
            version_field is None
            or version_field.field_type != "integer"
            or version_field.nullable
        ):
            raise AppDomainModelError(
                f"versioned entity {entity.entity_id} requires non-null integer version"
            )

    lifecycle_states = entity.lifecycle_states
    _require_unique_tokens(lifecycle_states, f"{entity.entity_id}.lifecycle_states")
    if not lifecycle_states:
        raise AppDomainModelError(f"entity {entity.entity_id} requires lifecycle states")
    if len(lifecycle_states) > 1:
        status_field = fields_by_name.get("status")
        if status_field is None or status_field.field_type != "string" or status_field.nullable:
            raise AppDomainModelError(
                f"stateful entity {entity.entity_id} requires non-null string status"
            )

    relationship_names = tuple(item.name for item in entity.relationships)
    _require_unique_tokens(relationship_names, f"{entity.entity_id}.relationships")
    for relationship in entity.relationships:
        _require_token(relationship.target_entity, "target_entity")
        if relationship.target_entity not in known_entities:
            raise AppDomainModelError(
                f"entity {entity.entity_id} relationship targets unknown entity "
                f"{relationship.target_entity}"
            )

    seen_indexes: set[tuple[str, ...]] = set()
    for index in entity.indexes:
        if not index:
            raise AppDomainModelError(f"entity {entity.entity_id} contains an empty index")
        _require_unique_tokens(index, f"{entity.entity_id}.index")
        if index in seen_indexes:
            raise AppDomainModelError(f"entity {entity.entity_id} contains duplicate indexes")
        seen_indexes.add(index)
        unknown_fields = tuple(field for field in index if field not in fields_by_name)
        if unknown_fields:
            raise AppDomainModelError(
                f"entity {entity.entity_id} index references unknown fields"
            )


def _entity_payload(entity: DomainEntity) -> dict[str, object]:
    return {
        "audit_required": entity.audit_required,
        "entity_id": entity.entity_id,
        "fields": [
            {
                "field_type": field.field_type,
                "indexed": field.indexed,
                "name": field.name,
                "nullable": field.nullable,
                "unique": field.unique,
            }
            for field in entity.fields
        ],
        "indexes": [list(index) for index in entity.indexes],
        "lifecycle_states": list(entity.lifecycle_states),
        "relationships": [
            {
                "kind": relationship.kind,
                "name": relationship.name,
                "nullable": relationship.nullable,
                "target_entity": relationship.target_entity,
            }
            for relationship in entity.relationships
        ],
        "tenant_owned": entity.tenant_owned,
        "versioned": entity.versioned,
    }


def _require_unique_tokens(values: tuple[str, ...], field: str) -> None:
    seen: set[str] = set()
    for value in values:
        _require_token(value, field)
        if value in seen:
            raise AppDomainModelError(f"{field} contains duplicate values")
        seen.add(value)


def _require_token(value: str, field: str) -> None:
    if not value or value != value.strip():
        raise AppDomainModelError(f"{field} must be non-blank and trimmed")


def _sha256_json(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

"""Deterministic Stage-2 enterprise application data/migration contracts.

This module is specification/planning only. It does not create schemas, connect to
databases, run migrations, mutate production data, access credentials, deploy,
sign, submit, publish, or create a second runtime/core. Real implementation stays
downstream through the canonical Software Factory and governance/evidence gates.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Literal

from services.app_architecture_plan import ApplicationArchitecturePlan
from services.app_domain_model import DomainModelPlan
from services.app_product_spec import ProductSpec


ConstraintKind = Literal["primary-key", "foreign-key", "unique", "check"]
MigrationRisk = Literal["low", "medium", "high", "critical"]
MigrationStepKind = Literal[
    "create-table",
    "add-column",
    "alter-column",
    "create-index",
    "add-constraint",
    "backfill",
    "data-transform",
]


class AppDataMigrationPlanError(ValueError):
    """Data/migration input is invalid, ambiguous, or violates enterprise invariants."""


@dataclass(frozen=True, slots=True)
class SchemaConstraint:
    constraint_id: str
    kind: ConstraintKind
    fields: tuple[str, ...]
    reference_entity: str | None = None
    reference_fields: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TablePlan:
    entity_id: str
    constraints: tuple[SchemaConstraint, ...]
    indexes: tuple[tuple[str, ...], ...]


@dataclass(frozen=True, slots=True)
class MigrationStep:
    step_id: str
    kind: MigrationStepKind
    entity_id: str
    description: str
    reversible: bool
    risk: MigrationRisk = "low"


@dataclass(frozen=True, slots=True)
class DataMigrationPlan:
    project_id: str
    spec_sha256: str
    architecture_plan_sha256: str
    domain_model_sha256: str
    tables: tuple[TablePlan, ...]
    steps: tuple[MigrationStep, ...]
    rollback_required: Literal[True]
    backup_readiness_required: Literal[True]
    validation_required_before_execution: Literal[True]
    production_approval_required: Literal[True]
    implementation_authority: Literal["software-factory"]
    direct_database_mutation_allowed: Literal[False]
    plan_sha256: str


def build_data_migration_plan(
    *,
    spec: ProductSpec,
    architecture: ApplicationArchitecturePlan,
    domain_model: DomainModelPlan,
    tables: tuple[TablePlan, ...],
    steps: tuple[MigrationStep, ...],
) -> DataMigrationPlan:
    """Validate an immutable schema/migration plan without granting mutation authority."""
    if architecture.project_id != spec.project_id or architecture.spec_sha256 != spec.spec_sha256:
        raise AppDataMigrationPlanError(
            "architecture plan must be bound to the supplied ProductSpec"
        )
    if (
        domain_model.project_id != spec.project_id
        or domain_model.spec_sha256 != spec.spec_sha256
        or domain_model.architecture_plan_sha256 != architecture.plan_sha256
    ):
        raise AppDataMigrationPlanError(
            "domain model must be bound to the supplied ProductSpec and architecture"
        )

    entity_ids = tuple(entity.entity_id for entity in domain_model.entities)
    known_entities = frozenset(entity_ids)
    table_ids = tuple(table.entity_id for table in tables)
    _require_unique_tokens(table_ids, "tables")

    if architecture.persistence_mode == "relational":
        if frozenset(table_ids) != known_entities:
            raise AppDataMigrationPlanError(
                "relational schema tables must exactly cover domain entities"
            )
    elif tables or steps:
        raise AppDataMigrationPlanError(
            "non-relational architecture cannot declare relational schema/migration steps"
        )

    fields_by_entity = {
        entity.entity_id: frozenset(field.name for field in entity.fields)
        for entity in domain_model.entities
    }

    for table in tables:
        _validate_table(
            table,
            known_entities=known_entities,
            fields_by_entity=fields_by_entity,
        )

    step_ids = tuple(step.step_id for step in steps)
    _require_unique_tokens(step_ids, "migration steps")
    for step in steps:
        _validate_step(step, known_entities=known_entities)

    if any(not step.reversible for step in steps):
        raise AppDataMigrationPlanError(
            "all planned migration steps must define a reversible path before execution"
        )

    canonical: dict[str, object] = {
        "architecture_plan_sha256": architecture.plan_sha256,
        "backup_readiness_required": True,
        "direct_database_mutation_allowed": False,
        "domain_model_sha256": domain_model.model_sha256,
        "implementation_authority": "software-factory",
        "production_approval_required": True,
        "project_id": spec.project_id,
        "rollback_required": True,
        "spec_sha256": spec.spec_sha256,
        "steps": [_step_payload(step) for step in steps],
        "tables": [_table_payload(table) for table in tables],
        "validation_required_before_execution": True,
    }
    return DataMigrationPlan(
        project_id=spec.project_id,
        spec_sha256=spec.spec_sha256,
        architecture_plan_sha256=architecture.plan_sha256,
        domain_model_sha256=domain_model.model_sha256,
        tables=tables,
        steps=steps,
        rollback_required=True,
        backup_readiness_required=True,
        validation_required_before_execution=True,
        production_approval_required=True,
        implementation_authority="software-factory",
        direct_database_mutation_allowed=False,
        plan_sha256=_sha256_json(canonical),
    )


def _validate_table(
    table: TablePlan,
    *,
    known_entities: frozenset[str],
    fields_by_entity: dict[str, frozenset[str]],
) -> None:
    _require_token(table.entity_id, "table.entity_id")
    if table.entity_id not in known_entities:
        raise AppDataMigrationPlanError("table references unknown domain entity")

    known_fields = fields_by_entity[table.entity_id]
    constraint_ids = tuple(item.constraint_id for item in table.constraints)
    _require_unique_tokens(constraint_ids, f"{table.entity_id}.constraints")

    primary_keys = 0
    for constraint in table.constraints:
        _require_token(constraint.constraint_id, "constraint_id")
        _require_unique_tokens(constraint.fields, f"{constraint.constraint_id}.fields")
        if not constraint.fields:
            raise AppDataMigrationPlanError("constraint fields cannot be empty")
        if any(field not in known_fields for field in constraint.fields):
            raise AppDataMigrationPlanError("constraint references unknown field")

        if constraint.kind == "primary-key":
            primary_keys += 1
            if constraint.fields != ("id",):
                raise AppDataMigrationPlanError("primary key must be the stable id field")
            if constraint.reference_entity is not None or constraint.reference_fields:
                raise AppDataMigrationPlanError("primary key cannot declare a reference")
        elif constraint.kind == "foreign-key":
            if constraint.reference_entity is None:
                raise AppDataMigrationPlanError("foreign key requires reference entity")
            if constraint.reference_entity not in known_entities:
                raise AppDataMigrationPlanError("foreign key references unknown entity")
            if not constraint.reference_fields:
                raise AppDataMigrationPlanError("foreign key requires reference fields")
            target_fields = fields_by_entity[constraint.reference_entity]
            if any(field not in target_fields for field in constraint.reference_fields):
                raise AppDataMigrationPlanError("foreign key references unknown target field")
            if len(constraint.fields) != len(constraint.reference_fields):
                raise AppDataMigrationPlanError("foreign key field cardinality mismatch")
        elif constraint.reference_entity is not None or constraint.reference_fields:
            raise AppDataMigrationPlanError("only foreign keys may declare a reference")

    if primary_keys != 1:
        raise AppDataMigrationPlanError(
            f"table {table.entity_id} requires exactly one primary-key constraint"
        )

    seen_indexes: set[tuple[str, ...]] = set()
    for index in table.indexes:
        if not index:
            raise AppDataMigrationPlanError("index fields cannot be empty")
        _require_unique_tokens(index, f"{table.entity_id}.index")
        if index in seen_indexes:
            raise AppDataMigrationPlanError("table contains duplicate indexes")
        seen_indexes.add(index)
        if any(field not in known_fields for field in index):
            raise AppDataMigrationPlanError("index references unknown field")


def _validate_step(step: MigrationStep, *, known_entities: frozenset[str]) -> None:
    _require_token(step.step_id, "step_id")
    _require_token(step.entity_id, "step.entity_id")
    _require_token(step.description, "step.description")
    if step.entity_id not in known_entities:
        raise AppDataMigrationPlanError("migration step references unknown domain entity")
    if step.risk in {"high", "critical"} and not step.reversible:
        raise AppDataMigrationPlanError(
            "high-risk migration step must be reversible before execution"
        )


def _table_payload(table: TablePlan) -> dict[str, object]:
    return {
        "constraints": [
            {
                "constraint_id": constraint.constraint_id,
                "fields": list(constraint.fields),
                "kind": constraint.kind,
                "reference_entity": constraint.reference_entity,
                "reference_fields": list(constraint.reference_fields),
            }
            for constraint in table.constraints
        ],
        "entity_id": table.entity_id,
        "indexes": [list(index) for index in table.indexes],
    }


def _step_payload(step: MigrationStep) -> dict[str, object]:
    return {
        "description": step.description,
        "entity_id": step.entity_id,
        "kind": step.kind,
        "reversible": step.reversible,
        "risk": step.risk,
        "step_id": step.step_id,
    }


def _require_unique_tokens(values: tuple[str, ...], field: str) -> None:
    seen: set[str] = set()
    for value in values:
        _require_token(value, field)
        if value in seen:
            raise AppDataMigrationPlanError(f"{field} contains duplicate values")
        seen.add(value)


def _require_token(value: str, field: str) -> None:
    if not value or value != value.strip():
        raise AppDataMigrationPlanError(f"{field} must be non-blank and trimmed")


def _sha256_json(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

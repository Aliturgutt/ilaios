from __future__ import annotations

import pytest

from services.app_architecture_plan import (
    ApplicationArchitecturePlan,
    plan_application_architecture,
)
from services.app_data_migration_plan import (
    AppDataMigrationPlanError,
    MigrationStep,
    SchemaConstraint,
    TablePlan,
    build_data_migration_plan,
)
from services.app_domain_model import (
    DomainEntity,
    DomainField,
    DomainModelPlan,
    DomainRelationship,
    build_domain_model,
)
from services.app_product_spec import (
    ProductSpec,
    admit_project,
    build_product_spec,
    classify_risk,
    resolve_capabilities,
)


def _spec() -> ProductSpec:
    admission = admit_project(
        project_id="project-data-migration-test",
        intent="new",
        objective="Build a governed collaborative application",
        platforms=("android", "ios"),
    )
    return build_product_spec(
        admission=admission,
        product_name="Data Migration Test",
        actors=("owner", "member"),
        screens=("projects", "tasks", "settings"),
        capabilities=("authentication", "rbac", "database", "projects", "workflows"),
    )


def _architecture(spec: ProductSpec) -> ApplicationArchitecturePlan:
    return plan_application_architecture(
        spec=spec,
        capability_assessments=resolve_capabilities(spec),
        risk=classify_risk(spec),
    )


def _project_entity() -> DomainEntity:
    return DomainEntity(
        entity_id="project",
        tenant_owned=True,
        versioned=True,
        lifecycle_states=("active", "archived"),
        fields=(
            DomainField("id", "uuid", unique=True),
            DomainField("tenant_id", "uuid", indexed=True),
            DomainField("name", "string", indexed=True),
            DomainField("status", "string", indexed=True),
            DomainField("version", "integer"),
            DomainField("created_at", "datetime"),
            DomainField("updated_at", "datetime"),
        ),
        indexes=(("tenant_id", "status"), ("tenant_id", "name")),
    )


def _task_entity() -> DomainEntity:
    return DomainEntity(
        entity_id="task",
        tenant_owned=True,
        lifecycle_states=("open", "done"),
        fields=(
            DomainField("id", "uuid", unique=True),
            DomainField("tenant_id", "uuid", indexed=True),
            DomainField("project_id", "uuid", indexed=True),
            DomainField("title", "string"),
            DomainField("status", "string", indexed=True),
            DomainField("created_at", "datetime"),
            DomainField("updated_at", "datetime"),
        ),
        relationships=(
            DomainRelationship(
                name="project",
                target_entity="project",
                kind="many-to-one",
            ),
        ),
        indexes=(("tenant_id", "project_id", "status"),),
    )


def _domain_model(spec: ProductSpec) -> DomainModelPlan:
    return build_domain_model(
        spec=spec,
        architecture=_architecture(spec),
        entities=(_project_entity(), _task_entity()),
    )


def _tables() -> tuple[TablePlan, ...]:
    return (
        TablePlan(
            entity_id="project",
            constraints=(
                SchemaConstraint("project_pk", "primary-key", ("id",)),
                SchemaConstraint("project_name_unique", "unique", ("tenant_id", "name")),
            ),
            indexes=(("tenant_id", "status"), ("tenant_id", "name")),
        ),
        TablePlan(
            entity_id="task",
            constraints=(
                SchemaConstraint("task_pk", "primary-key", ("id",)),
                SchemaConstraint(
                    "task_project_fk",
                    "foreign-key",
                    ("project_id",),
                    reference_entity="project",
                    reference_fields=("id",),
                ),
            ),
            indexes=(("tenant_id", "project_id", "status"),),
        ),
    )


def _steps() -> tuple[MigrationStep, ...]:
    return (
        MigrationStep(
            step_id="001-create-project",
            kind="create-table",
            entity_id="project",
            description="Create project table and constraints",
            reversible=True,
        ),
        MigrationStep(
            step_id="002-create-task",
            kind="create-table",
            entity_id="task",
            description="Create task table and foreign key",
            reversible=True,
        ),
    )


def test_data_migration_plan_binds_authority_and_safety_requirements() -> None:
    spec = _spec()
    architecture = _architecture(spec)
    domain_model = _domain_model(spec)

    plan = build_data_migration_plan(
        spec=spec,
        architecture=architecture,
        domain_model=domain_model,
        tables=_tables(),
        steps=_steps(),
    )

    assert plan.project_id == spec.project_id
    assert plan.domain_model_sha256 == domain_model.model_sha256
    assert plan.rollback_required is True
    assert plan.backup_readiness_required is True
    assert plan.validation_required_before_execution is True
    assert plan.production_approval_required is True
    assert plan.implementation_authority == "software-factory"
    assert plan.direct_database_mutation_allowed is False
    assert len(plan.plan_sha256) == 64


def test_data_migration_plan_is_deterministic_for_identical_inputs() -> None:
    spec = _spec()
    architecture = _architecture(spec)
    domain_model = _domain_model(spec)

    first = build_data_migration_plan(
        spec=spec,
        architecture=architecture,
        domain_model=domain_model,
        tables=_tables(),
        steps=_steps(),
    )
    second = build_data_migration_plan(
        spec=spec,
        architecture=architecture,
        domain_model=domain_model,
        tables=_tables(),
        steps=_steps(),
    )

    assert first == second
    assert first.plan_sha256 == second.plan_sha256


def test_relational_schema_must_cover_every_domain_entity() -> None:
    spec = _spec()
    architecture = _architecture(spec)
    domain_model = _domain_model(spec)

    with pytest.raises(AppDataMigrationPlanError, match="exactly cover"):
        build_data_migration_plan(
            spec=spec,
            architecture=architecture,
            domain_model=domain_model,
            tables=(_tables()[0],),
            steps=_steps(),
        )


def test_foreign_key_must_reference_known_target_field() -> None:
    spec = _spec()
    architecture = _architecture(spec)
    domain_model = _domain_model(spec)
    invalid_task = TablePlan(
        entity_id="task",
        constraints=(
            SchemaConstraint("task_pk", "primary-key", ("id",)),
            SchemaConstraint(
                "task_project_fk",
                "foreign-key",
                ("project_id",),
                reference_entity="project",
                reference_fields=("missing",),
            ),
        ),
        indexes=(("tenant_id", "project_id", "status"),),
    )

    with pytest.raises(AppDataMigrationPlanError, match="unknown target field"):
        build_data_migration_plan(
            spec=spec,
            architecture=architecture,
            domain_model=domain_model,
            tables=(_tables()[0], invalid_task),
            steps=_steps(),
        )


def test_migration_step_requires_reversible_path() -> None:
    spec = _spec()
    architecture = _architecture(spec)
    domain_model = _domain_model(spec)
    irreversible = MigrationStep(
        step_id="001-destructive-transform",
        kind="data-transform",
        entity_id="project",
        description="Destructive rewrite",
        reversible=False,
        risk="critical",
    )

    with pytest.raises(AppDataMigrationPlanError, match="reversible"):
        build_data_migration_plan(
            spec=spec,
            architecture=architecture,
            domain_model=domain_model,
            tables=_tables(),
            steps=(irreversible,),
        )


def test_data_migration_rejects_domain_model_from_other_product() -> None:
    spec = _spec()
    architecture = _architecture(spec)
    other_admission = admit_project(
        project_id="other-data-project",
        intent="new",
        objective="Other data product",
        platforms=("android",),
    )
    other_spec = build_product_spec(
        admission=other_admission,
        product_name="Other Data",
        actors=("owner",),
        screens=("home",),
        capabilities=("database",),
    )
    other_model = build_domain_model(
        spec=other_spec,
        architecture=_architecture(other_spec),
        entities=(_project_entity(),),
    )

    with pytest.raises(AppDataMigrationPlanError, match="domain model must be bound"):
        build_data_migration_plan(
            spec=spec,
            architecture=architecture,
            domain_model=other_model,
            tables=_tables(),
            steps=_steps(),
        )

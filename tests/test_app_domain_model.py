from __future__ import annotations

import pytest

from services.app_architecture_plan import (
    ApplicationArchitecturePlan,
    plan_application_architecture,
)
from services.app_domain_model import (
    AppDomainModelError,
    DomainEntity,
    DomainField,
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
        project_id="project-domain-test",
        intent="new",
        objective="Build a governed collaborative application",
        platforms=("android", "ios"),
    )
    return build_product_spec(
        admission=admission,
        product_name="Domain Test",
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


def test_domain_model_binds_tenant_owned_entities_and_authority() -> None:
    spec = _spec()
    plan = build_domain_model(
        spec=spec,
        architecture=_architecture(spec),
        entities=(_project_entity(), _task_entity()),
    )

    assert plan.project_id == spec.project_id
    assert plan.spec_sha256 == spec.spec_sha256
    assert plan.tenant_isolation_required is True
    assert plan.stable_ids_required is True
    assert plan.timestamps_required is True
    assert plan.implementation_authority == "software-factory"
    assert plan.direct_database_mutation_allowed is False
    assert len(plan.model_sha256) == 64


def test_domain_model_is_deterministic_for_identical_inputs() -> None:
    spec = _spec()
    architecture = _architecture(spec)
    entities = (_project_entity(), _task_entity())

    first = build_domain_model(spec=spec, architecture=architecture, entities=entities)
    second = build_domain_model(spec=spec, architecture=architecture, entities=entities)

    assert first == second
    assert first.model_sha256 == second.model_sha256


def test_tenant_owned_entity_requires_indexed_tenant_id() -> None:
    spec = _spec()
    invalid = DomainEntity(
        entity_id="project",
        tenant_owned=True,
        fields=(
            DomainField("id", "uuid", unique=True),
            DomainField("tenant_id", "uuid"),
            DomainField("created_at", "datetime"),
            DomainField("updated_at", "datetime"),
        ),
    )

    with pytest.raises(AppDomainModelError, match="indexed uuid tenant_id"):
        build_domain_model(
            spec=spec,
            architecture=_architecture(spec),
            entities=(invalid,),
        )


def test_domain_relationship_must_target_known_entity() -> None:
    spec = _spec()
    task = DomainEntity(
        entity_id="task",
        tenant_owned=True,
        fields=(
            DomainField("id", "uuid", unique=True),
            DomainField("tenant_id", "uuid", indexed=True),
            DomainField("created_at", "datetime"),
            DomainField("updated_at", "datetime"),
        ),
        relationships=(
            DomainRelationship(
                name="missing",
                target_entity="missing-project",
                kind="many-to-one",
            ),
        ),
    )

    with pytest.raises(AppDomainModelError, match="unknown entity"):
        build_domain_model(
            spec=spec,
            architecture=_architecture(spec),
            entities=(task,),
        )


def test_domain_model_rejects_architecture_from_other_product_spec() -> None:
    spec = _spec()
    other_admission = admit_project(
        project_id="other-project",
        intent="new",
        objective="Other product",
        platforms=("android",),
    )
    other_spec = build_product_spec(
        admission=other_admission,
        product_name="Other",
        actors=("owner",),
        screens=("home",),
        capabilities=("database",),
    )

    with pytest.raises(AppDomainModelError, match="bound to the supplied ProductSpec"):
        build_domain_model(
            spec=spec,
            architecture=_architecture(other_spec),
            entities=(_project_entity(),),
        )


def test_relational_architecture_requires_domain_entity() -> None:
    spec = _spec()

    with pytest.raises(AppDomainModelError, match="requires at least one domain entity"):
        build_domain_model(spec=spec, architecture=_architecture(spec), entities=())

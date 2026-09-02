"""E2E proof that persistent company Knowledge reaches the canonical Web factory."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import cast

import pytest

from services.control_plane import ControlPlane, ControlPlaneConfig
from services.control_plane.workflows import WorkflowStore, WorkflowStoreConfig
from services.evidence import EvidenceStore
from services.execution_adapters import register_web_runtime
from services.execution_coordinator import ExecutionCoordinator, ExecutionState
from services.governance import GovernedRuntimeGateway
from services.integrations import DeterministicLocalVideoRuntime, DurableVideoProductRuntime
from services.integrations.company_knowledge_web import (
    CompanyKnowledgeWebError,
    execute_web_with_company_knowledge,
)
from services.integrations.web_product_runtime import DurableWebProductRuntime
from services.knowledge_runtime import (
    DurableKnowledgeRuntime,
    KnowledgeRuntimeConfig,
    KnowledgeRuntimePolicy,
)
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime


def _knowledge(tmp_path: Path, tenant_id: str = "tenant/web") -> DurableKnowledgeRuntime:
    return DurableKnowledgeRuntime(
        KnowledgeRuntimeConfig(
            metadata_database=tmp_path / "knowledge.sqlite3",
            vector_database=tmp_path / "knowledge-vectors.sqlite3",
            policy=KnowledgeRuntimePolicy(
                principal_id="service-company-knowledge",
                tenant_id=tenant_id,
                project_id="project/company-web",
                allowed_classifications=frozenset({"INTERNAL"}),
                allowed_purposes=frozenset({"build"}),
                allowed_residencies=frozenset({"eu"}),
            ),
        )
    )


def _coordinator(tmp_path: Path) -> ExecutionCoordinator:
    state = tmp_path / "state.sqlite3"
    control = ControlPlane(ControlPlaneConfig(state, "token"))
    workflows = WorkflowStore(WorkflowStoreConfig(state))
    scheduler = DurableWorkerScheduler(state, lease_duration=timedelta(seconds=30))
    grants = DurableGrantPolicy(state)
    evidence = EvidenceStore(tmp_path / "evidence")
    governance = GovernedRuntimeGateway(
        tmp_path / "governance.sqlite3",
        GovernedRuntime(state),
        hard_cap_minor=100,
    )
    video = DeterministicLocalVideoRuntime(tmp_path / "video", grants, governance, evidence)
    video_product = DurableVideoProductRuntime(
        tmp_path / "video-product.sqlite3",
        control,
        workflows,
        scheduler,
        grants,
        governance,
        video,
    )
    web = DurableWebProductRuntime(
        tmp_path / "web-product.sqlite3",
        control,
        grants,
        governance,
        tmp_path / "web",
    )
    coordinator = ExecutionCoordinator(
        tmp_path / "coordinator.sqlite3",
        control,
        governance,
        grants,
        video_product,
        evidence,
    )
    register_web_runtime(coordinator, web)
    return coordinator


def test_persistent_company_knowledge_reaches_real_web_factory_after_restart(
    tmp_path: Path,
) -> None:
    knowledge = _knowledge(tmp_path)
    knowledge.ingest_source(
        source_id="brand-guidelines",
        locator="company://brand-guidelines.docx",
        content=(
            "Acme Robotics uses concise enterprise copy, dark graphite surfaces, "
            "and cyan only for primary actions."
        ),
        trusted=True,
        classifications=frozenset({"INTERNAL"}),
        purposes=frozenset({"build"}),
        residency="eu",
    )
    restarted = _knowledge(tmp_path)
    coordinator = _coordinator(tmp_path)
    result = execute_web_with_company_knowledge(
        coordinator,
        restarted,
        request_id="web-company-knowledge-1",
        objective="Build a premium corporate website for Acme Robotics",
        token="token",
        principal_id="oidc|owner@example.test",
        tenant_id="tenant/web",
        now=datetime(2026, 9, 2, 9, 0, tzinfo=timezone.utc),
    )

    assert result["source_ids"] == ["brand-guidelines"]
    assert result["context_evidence_sha256"]
    prepared = cast(dict[str, object], result["prepared"])
    manifest = cast(dict[str, object], result["manifest"])
    assert prepared["execution_status"] == ExecutionState.ADMITTED.value
    assert manifest["accepted"] is True
    assert manifest["adapter_id"] == "web.product-runtime.v1"
    assert manifest["source_project_digest"]


def test_company_knowledge_web_e2e_denies_cross_tenant_execution(tmp_path: Path) -> None:
    knowledge = _knowledge(tmp_path, tenant_id="tenant/a")
    knowledge.ingest_source(
        source_id="private-guidelines",
        locator="company://private.pdf",
        content="Tenant A private company guidance",
        trusted=True,
        classifications=frozenset({"INTERNAL"}),
        purposes=frozenset({"build"}),
        residency="eu",
    )

    with pytest.raises(CompanyKnowledgeWebError, match="tenant"):
        execute_web_with_company_knowledge(
            _coordinator(tmp_path),
            knowledge,
            request_id="cross-tenant-denied",
            objective="Build a company website",
            token="token",
            principal_id="oidc|owner@example.test",
            tenant_id="tenant/b",
            now=datetime(2026, 9, 2, 9, 0, tzinfo=timezone.utc),
        )

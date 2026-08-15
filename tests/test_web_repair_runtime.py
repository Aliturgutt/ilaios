"""End-to-end bounded repair coverage for the Web finished-product runtime."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import cast

from services.control_plane import ControlPlane, ControlPlaneConfig
from services.control_plane.workflows import WorkflowStore, WorkflowStoreConfig
from services.evidence import EvidenceStore
from services.execution_coordinator import ExecutionCoordinator
from services.governance import GovernedRuntimeGateway
from services.integrations import (
    DeterministicLocalVideoRuntime,
    DurableVideoProductRuntime,
    DurableWebProductRuntime,
)
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime


def _coordinator(tmp_path: Path) -> ExecutionCoordinator:
    state = tmp_path / "state.sqlite3"
    control = ControlPlane(ControlPlaneConfig(state, "token"))
    workflows = WorkflowStore(WorkflowStoreConfig(state))
    scheduler = DurableWorkerScheduler(state, lease_duration=timedelta(seconds=30))
    grants = DurableGrantPolicy(state)
    governance = GovernedRuntimeGateway(
        tmp_path / "governance.sqlite3",
        GovernedRuntime(state),
        hard_cap_minor=100,
    )
    video = DeterministicLocalVideoRuntime(
        tmp_path / "video",
        grants,
        governance,
        EvidenceStore(tmp_path / "evidence"),
    )
    product = DurableVideoProductRuntime(
        tmp_path / "product.sqlite3",
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
    return ExecutionCoordinator(
        tmp_path / "coordinator.sqlite3",
        control,
        governance,
        grants,
        product,
        web,
    )


def test_runtime_repairs_once_persists_repaired_spec_and_records_hashes(
    tmp_path: Path,
) -> None:
    coordinator = _coordinator(tmp_path)
    now = datetime(2026, 8, 16, 0, 0, tzinfo=timezone.utc)
    request_id = "exec-web-repair"
    coordinator.prepare(
        request_id,
        "Build a premium bilingual Turkish/English website for a corporate law firm",
        token="token",
        principal_id="oidc|repair@example.test",
        tenant_id="tenant/repair",
        now=now,
    )

    database = tmp_path / "web-product.sqlite3"
    with sqlite3.connect(database) as connection:
        raw = connection.execute(
            "SELECT spec_json FROM web_product_requests WHERE request_id = ?",
            (request_id,),
        ).fetchone()
        assert raw is not None
        spec = cast(dict[str, object], json.loads(str(raw[0])))
        spec["pages"] = ["about", "about"]
        spec["locales"] = ["fr"]
        connection.execute(
            "UPDATE web_product_requests SET spec_json = ? WHERE request_id = ?",
            (json.dumps(spec, sort_keys=True), request_id),
        )

    manifest = coordinator.resume(
        request_id,
        token="token",
        now=now + timedelta(seconds=1),
    )
    assert manifest["accepted"] is True
    policy = cast(dict[str, object], manifest["repair_policy"])
    assert policy == {"max_attempts": 1, "attempts_used": 1}
    attempts = cast(list[dict[str, object]], manifest["repair_attempts"])
    assert len(attempts) == 1
    assert attempts[0]["attempt"] == 1
    assert attempts[0]["before_spec_hash"] != attempts[0]["after_spec_hash"]

    with sqlite3.connect(database) as connection:
        repaired_row = connection.execute(
            "SELECT spec_json, status FROM web_product_requests WHERE request_id = ?",
            (request_id,),
        ).fetchone()
    assert repaired_row is not None
    repaired_spec = cast(dict[str, object], json.loads(str(repaired_row[0])))
    assert repaired_spec["pages"] == ["home", "about", "contact"]
    assert repaired_spec["locales"] == ["en"]
    assert repaired_row[1] == "accepted"

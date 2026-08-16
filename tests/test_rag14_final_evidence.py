"""Final RAG.14 evidence packaging must never convert partial evidence to READY."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from services.rag14_final_evidence import assemble


_SOURCE = "a" * 40
_DIGEST = "sha256:" + ("b" * 64)


def _write(root: Path, relative: str, payload: dict[str, object]) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _complete_except_finops_and_bad_rollback(root: Path) -> None:
    _write(
        root,
        "release-binding.json",
        {
            "runtime_source_sha": _SOURCE,
            "image_digest": _DIGEST,
            "release_state": "CANARY",
            "production_authority": False,
        },
    )
    _write(
        root,
        "deployment-task-definition.json",
        {
            "task_definition_arn": "arn:aws:ecs:eu-central-1:101180464425:task-definition/ilaios:1",
            "image": f"repo@{_DIGEST}",
        },
    )
    _write(
        root,
        "startup-selftest.json",
        {
            "status": "PASS",
            "embedding_dimensions": 384,
            "top1_passes": 6,
            "required_top1_cases": 6,
            "production_authority": False,
        },
    )
    _write(
        root,
        "live-redteam/verify-after-restart.json",
        {"event_chain": "verified", "vector_index_integrity": True},
    )
    _write(
        root,
        "live-redteam/state-after-restart.json",
        {"vector_index": {"integrity_ok": True, "row_count": 0}},
    )
    _write(
        root,
        "cross-tenant-fargate.json",
        {
            "status": "PASS",
            "scope_binding_rejected": True,
            "production_authority": False,
        },
    )
    for relative in (
        "live-redteam/unauthenticated.json",
        "live-redteam/cross-scope.json",
        "live-redteam/restricted-classification.json",
        "live-redteam/residency-denied.json",
        "live-redteam/purpose-denied.json",
    ):
        _write(root, relative, {"error": "denied"})
    _write(
        root,
        "live-redteam/state-after-quarantine.json",
        {"metrics": {"quarantined_units": 2}},
    )
    _write(
        root,
        "live-redteam/retrieval-safe-only.json",
        {"units": [{"source_id": "safe-source"}]},
    )
    _write(
        root,
        "backup-restore.json",
        {
            "status": "PASS",
            "corrupt_restore_rejected": True,
            "restored_vector_row_count": 0,
            "production_authority": False,
        },
    )
    _write(
        root,
        "observability-alerts.json",
        {
            "status": "PASS",
            "all_rules_fired": True,
            "all_rules_recovered": True,
        },
    )
    _write(
        root,
        "deployment-health-window.json",
        {"status": "PASS", "sample_count": 12, "production_authority": False},
    )
    _write(
        root,
        "finops-resource-meter.json",
        {
            "status": "PASS",
            "external_spend_approved": True,
            "currency_cost_claimed": False,
            "budget_guard_active": False,
            "production_authority": False,
        },
    )
    _write(
        root,
        "rollback-recovery.json",
        {
            "status": "PASS",
            "bad_deployment_simulated": False,
            "rollback_to_verified_artifact": True,
            "production_authority": False,
        },
    )


def test_partial_runtime_evidence_remains_blocked(tmp_path: Path) -> None:
    _complete_except_finops_and_bad_rollback(tmp_path)

    report = assemble(tmp_path)

    assert report["status"] == "BLOCKED"
    assert report["production_approved"] is False
    missing = report["missing_requirements"]
    assert isinstance(missing, list)
    assert set(cast(list[str], missing)) == {
        "production_routing_finops",
        "rollback_recovery",
    }
    assert report["exact_release_scope"] == f"source:{_SOURCE}@image:{_DIGEST}"


def test_complete_evidence_can_only_reach_governed_review(tmp_path: Path) -> None:
    _complete_except_finops_and_bad_rollback(tmp_path)
    _write(
        tmp_path,
        "finops-resource-meter.json",
        {
            "status": "PASS",
            "external_spend_approved": True,
            "currency_cost_claimed": True,
            "budget_guard_active": True,
            "production_authority": False,
        },
    )
    _write(
        tmp_path,
        "rollback-recovery.json",
        {
            "status": "PASS",
            "bad_deployment_simulated": True,
            "rollback_to_verified_artifact": True,
            "production_authority": False,
        },
    )

    report = assemble(tmp_path)

    assert report["status"] == "READY_FOR_GOVERNED_PROMOTION_REVIEW"
    assert report["missing_requirements"] == []
    assert report["production_approved"] is False
    satisfied = report["satisfied_requirements"]
    assert isinstance(satisfied, list)
    for requirement in cast(list[str], satisfied):
        assert (tmp_path / "final-evidence-items" / f"{requirement}.json").is_file()

"""Assemble the fail-closed RAG.14 final evidence package.

The assembler never manufactures missing production evidence. It validates
observed canary artifacts, binds every accepted proof to the same exact source
SHA/image digest scope, and feeds only satisfied requirements into the
canonical RAG14PromotionGate.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import cast

from services.knowledge_rag_production import (
    RAG14EvidenceItem,
    RAG14PromotionGate,
    RAG14_REQUIREMENTS,
)


class RAG14FinalEvidenceError(RuntimeError):
    """The final evidence package itself is malformed or cross-scoped."""


_VERIFIER = "ilaios.rag14.runtime-evidence.v1"


def _load(path: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        raise RAG14FinalEvidenceError(
            f"required evidence file is missing or unsafe: {path}"
        )
    try:
        value: object = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RAG14FinalEvidenceError(f"invalid JSON evidence: {path}") from error
    if not isinstance(value, dict):
        raise RAG14FinalEvidenceError(f"evidence must be a JSON object: {path}")
    return cast(dict[str, object], value)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bundle(
    root: Path,
    requirement: str,
    members: tuple[str, ...],
    exact_release_scope: str,
) -> RAG14EvidenceItem:
    material: list[dict[str, str]] = []
    for relative in members:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise RAG14FinalEvidenceError(
                f"accepted requirement references missing evidence: {relative}"
            )
        material.append({"ref": relative, "sha256": _sha(path)})
    bundle = {
        "requirement": requirement,
        "exact_release_scope": exact_release_scope,
        "verified_by": _VERIFIER,
        "members": material,
        "production_authority": False,
    }
    directory = root / "final-evidence-items"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{requirement}.json"
    path.write_text(
        json.dumps(bundle, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return RAG14EvidenceItem(
        requirement=requirement,
        evidence_ref=f"artifact://rag14/{path.relative_to(root).as_posix()}",
        evidence_sha256=_sha(path),
        verified_by=_VERIFIER,
        exact_release_scope=exact_release_scope,
    )


def _safe_json(root: Path, relative: str) -> dict[str, object] | None:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        return None
    try:
        return _load(path)
    except RAG14FinalEvidenceError:
        return None


def _release_scope(root: Path) -> str:
    release = _load(root / "release-binding.json")
    source = release.get("runtime_source_sha")
    digest = release.get("image_digest")
    if (
        not isinstance(source, str)
        or len(source) != 40
        or any(character not in "0123456789abcdef" for character in source)
    ):
        raise RAG14FinalEvidenceError("release binding source SHA is invalid")
    if (
        not isinstance(digest, str)
        or not digest.startswith("sha256:")
        or len(digest) != 71
        or any(character not in "0123456789abcdef" for character in digest[7:])
    ):
        raise RAG14FinalEvidenceError("release binding image digest is invalid")
    if release.get("production_authority") not in {False, None}:
        raise RAG14FinalEvidenceError(
            "release evidence attempted to claim production authority"
        )
    return f"source:{source}@image:{digest}"


def _integer(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _satisfied_checks(root: Path) -> dict[str, tuple[bool, tuple[str, ...]]]:
    startup = _safe_json(root, "startup-selftest.json") or {}
    verify = _safe_json(root, "live-redteam/verify-after-restart.json") or {}
    restart_state = _safe_json(root, "live-redteam/state-after-restart.json") or {}
    quarantine = _safe_json(root, "live-redteam/state-after-quarantine.json") or {}
    retrieval = _safe_json(root, "live-redteam/retrieval-safe-only.json") or {}
    cross_tenant = _safe_json(root, "cross-tenant-fargate.json") or {}
    backup = _safe_json(root, "backup-restore.json") or {}
    alerts = _safe_json(root, "observability-alerts.json") or {}
    health = _safe_json(root, "deployment-health-window.json") or {}
    finops = _safe_json(root, "finops-resource-meter.json") or {}
    rollback = _safe_json(root, "rollback-recovery.json") or {}
    release = _safe_json(root, "release-binding.json") or {}
    deployment = _safe_json(root, "deployment-task-definition.json") or {}

    vector = restart_state.get("vector_index")
    metrics = quarantine.get("metrics")
    units = retrieval.get("units")
    startup_ok = (
        startup.get("status") == "PASS"
        and startup.get("embedding_dimensions") == 384
        and startup.get("top1_passes") == 6
        and startup.get("required_top1_cases") == 6
        and startup.get("production_authority") is False
    )
    vector_ok = (
        verify.get("event_chain") == "verified"
        and verify.get("vector_index_integrity") is True
        and isinstance(vector, dict)
        and vector.get("integrity_ok") is True
    )
    deletion_ok = (
        vector_ok
        and isinstance(vector, dict)
        and _integer(vector.get("row_count")) == 0
    )
    quarantine_ok = (
        isinstance(metrics, dict)
        and (_integer(metrics.get("quarantined_units")) or 0) >= 2
    )
    leakage_sources: set[str] = set()
    if isinstance(units, list):
        for item in units:
            if isinstance(item, dict):
                leakage_sources.add(str(item.get("source_id")))
    leakage_ok = (
        isinstance(units, list)
        and leakage_sources == {"safe-source"}
        and cross_tenant.get("scope_binding_rejected") is True
    )
    auth_members = (
        "live-redteam/unauthenticated.json",
        "live-redteam/cross-scope.json",
        "live-redteam/restricted-classification.json",
        "live-redteam/residency-denied.json",
        "live-redteam/purpose-denied.json",
    )
    auth_ok = all((root / member).is_file() for member in auth_members)
    backup_ok = (
        backup.get("status") == "PASS"
        and backup.get("corrupt_restore_rejected") is True
        and backup.get("restored_vector_row_count") == 0
        and backup.get("production_authority") is False
    )
    observability_ok = (
        alerts.get("status") == "PASS"
        and alerts.get("all_rules_fired") is True
        and alerts.get("all_rules_recovered") is True
        and health.get("status") == "PASS"
        and (_integer(health.get("sample_count")) or 0) >= 12
        and startup_ok
    )
    finops_ok = (
        finops.get("status") == "PASS"
        and finops.get("external_spend_approved") is True
        and finops.get("currency_cost_claimed") is True
        and finops.get("budget_guard_active") is True
        and finops.get("production_authority") is False
    )
    exact_artifact_ok = (
        release.get("release_state") == "CANARY"
        and isinstance(release.get("runtime_source_sha"), str)
        and isinstance(release.get("image_digest"), str)
        and isinstance(deployment.get("image"), str)
        and str(release.get("image_digest")) in str(deployment.get("image"))
    )
    deployment_ok = exact_artifact_ok and isinstance(
        deployment.get("task_definition_arn"), str
    )
    rollback_ok = (
        rollback.get("status") == "PASS"
        and rollback.get("bad_deployment_simulated") is True
        and rollback.get("rollback_to_verified_artifact") is True
        and rollback.get("production_authority") is False
    )

    return {
        "production_embedding_provider": (startup_ok, ("startup-selftest.json",)),
        "durable_vector_index": (
            vector_ok,
            (
                "live-redteam/verify-after-restart.json",
                "live-redteam/state-after-restart.json",
            ),
        ),
        "production_tenant_isolation": (
            cross_tenant.get("status") == "PASS"
            and cross_tenant.get("scope_binding_rejected") is True,
            ("cross-tenant-fargate.json",),
        ),
        "production_authorization_policy": (auth_ok, auth_members),
        "production_dlp_and_injection_controls": (
            quarantine_ok,
            ("live-redteam/state-after-quarantine.json",),
        ),
        "production_leakage_redteam": (
            leakage_ok,
            (
                "live-redteam/retrieval-safe-only.json",
                "cross-tenant-fargate.json",
            ),
        ),
        "production_backup_restore": (backup_ok, ("backup-restore.json",)),
        "production_deletion_reconciliation": (
            deletion_ok,
            (
                "live-redteam/state-after-restart.json",
                "live-redteam/verify-after-restart.json",
            ),
        ),
        "production_observability_slo": (
            observability_ok,
            (
                "observability-alerts.json",
                "deployment-health-window.json",
                "startup-selftest.json",
            ),
        ),
        "production_routing_finops": (finops_ok, ("finops-resource-meter.json",)),
        "exact_release_artifact": (
            exact_artifact_ok,
            ("release-binding.json", "deployment-task-definition.json"),
        ),
        "exact_deployment_result": (
            deployment_ok,
            ("deployment-task-definition.json", "deployment-health-window.json"),
        ),
        "deployment_health": (
            health.get("status") == "PASS",
            ("deployment-health-window.json",),
        ),
        "rollback_recovery": (rollback_ok, ("rollback-recovery.json",)),
    }


def assemble(root: Path) -> dict[str, object]:
    exact_scope = _release_scope(root)
    checks = _satisfied_checks(root)
    if set(checks) != set(RAG14_REQUIREMENTS):
        raise RAG14FinalEvidenceError("RAG.14 evidence assembler requirement drift")
    items: list[RAG14EvidenceItem] = []
    unsatisfied_reasons: dict[str, str] = {}
    for requirement in RAG14_REQUIREMENTS:
        satisfied, members = checks[requirement]
        if satisfied:
            items.append(_bundle(root, requirement, members, exact_scope))
        else:
            unsatisfied_reasons[requirement] = (
                "required live evidence absent or not strong enough"
            )

    gate = RAG14PromotionGate().evaluate(tuple(items))
    report: dict[str, object] = {
        "status": gate.status,
        "satisfied_requirements": list(gate.satisfied_requirements),
        "missing_requirements": list(gate.missing_requirements),
        "gate_evidence_sha256": gate.evidence_sha256,
        "exact_release_scope": exact_scope,
        "verified_by": _VERIFIER,
        "unsatisfied_reasons": unsatisfied_reasons,
        "production_approved": gate.production_approved,
    }
    (root / "rag14-promotion-gate.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    root = Path(os.environ.get("RAG14_EVIDENCE_ROOT", "rag14-evidence"))
    report = assemble(root)
    print(json.dumps({"event": "rag14_promotion_gate", **report}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

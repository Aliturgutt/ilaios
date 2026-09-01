"""RAG.14 canary approval must be fresh, exact and fail closed."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.rag14_canary_approval import (
    RAG14CanaryApprovalError,
    load_and_validate_canary_approval,
)
from services.rag14_embedding_provider import PRODUCTION_EMBEDDING_MODE


SOURCE_SHA = "9" * 40
IMAGE_DIGEST = "sha256:" + "a" * 64


def _approval() -> dict[str, object]:
    return {
        "approval": "RAG.14 CANARY EVIDENCE APPROVED",
        "external_spend_approval": True,
        "runtime_source_sha": SOURCE_SHA,
        "image_digest": IMAGE_DIGEST,
        "canary_ipv4_cidr": "203.0.113.7/32",
        "canary_tenant_id": "rag14-canary-tenant",
        "canary_project_id": "rag14-canary-project",
        "knowledge_principal_id": "service-rag-canary",
        "classifications": ["PUBLIC", "INTERNAL"],
        "purposes": ["build", "research"],
        "residencies": ["eu"],
        "embedding_mode": "verification_hash_v1",
    }


def _write(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def test_valid_approval_binds_source_image_network_and_terraform_values(tmp_path: Path) -> None:
    path = tmp_path / "approval.json"
    _write(path, _approval())

    approval = load_and_validate_canary_approval(
        path,
        expected_runtime_source_sha=SOURCE_SHA,
        expected_image_digest=IMAGE_DIGEST,
    )

    assert approval.canary_ipv4_cidr == "203.0.113.7/32"
    assert len(approval.evidence_sha256) == 64
    environment = approval.terraform_environment()
    assert environment["TF_VAR_release_state"] == "CANARY"
    assert environment["TF_VAR_knowledge_enabled"] == "true"
    assert environment["TF_VAR_image_digest"] == IMAGE_DIGEST
    assert environment["TF_VAR_knowledge_embedding_mode"] == "verification_hash_v1"


def test_pinned_production_provider_is_allowed_for_canary_evidence(tmp_path: Path) -> None:
    path = tmp_path / "approval.json"
    payload = _approval()
    payload["embedding_mode"] = PRODUCTION_EMBEDDING_MODE
    _write(path, payload)

    approval = load_and_validate_canary_approval(
        path,
        expected_runtime_source_sha=SOURCE_SHA,
        expected_image_digest=IMAGE_DIGEST,
    )

    assert approval.embedding_mode == PRODUCTION_EMBEDDING_MODE
    assert approval.terraform_environment()["TF_VAR_knowledge_embedding_mode"] == (
        PRODUCTION_EMBEDDING_MODE
    )


def test_stale_source_or_image_binding_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "approval.json"
    _write(path, _approval())

    with pytest.raises(RAG14CanaryApprovalError, match="runtime source SHA"):
        load_and_validate_canary_approval(
            path,
            expected_runtime_source_sha="8" * 40,
            expected_image_digest=IMAGE_DIGEST,
        )
    with pytest.raises(RAG14CanaryApprovalError, match="immutable image digest"):
        load_and_validate_canary_approval(
            path,
            expected_runtime_source_sha=SOURCE_SHA,
            expected_image_digest="sha256:" + "b" * 64,
        )


def test_old_generic_release_approval_shape_is_not_reusable(tmp_path: Path) -> None:
    path = tmp_path / "approval.json"
    _write(
        path,
        {
            "approval": "RELEASE.R01 CANARY APPLY APPROVED",
            "external_spend_approval": True,
            "canary_ipv4_cidr": "203.0.113.7/32",
            "canary_tenant_id": "ilaios-r01-canary",
            "retry_nonce": "old-release-approval",
        },
    )

    with pytest.raises(RAG14CanaryApprovalError, match="fields"):
        load_and_validate_canary_approval(
            path,
            expected_runtime_source_sha=SOURCE_SHA,
            expected_image_digest=IMAGE_DIGEST,
        )


def test_missing_spend_approval_or_non_32_network_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "approval.json"
    payload = _approval()
    payload["external_spend_approval"] = False
    _write(path, payload)
    with pytest.raises(RAG14CanaryApprovalError, match="spend"):
        load_and_validate_canary_approval(
            path,
            expected_runtime_source_sha=SOURCE_SHA,
            expected_image_digest=IMAGE_DIGEST,
        )

    payload = _approval()
    payload["canary_ipv4_cidr"] = "203.0.113.0/24"
    _write(path, payload)
    with pytest.raises(RAG14CanaryApprovalError, match="IPv4 /32"):
        load_and_validate_canary_approval(
            path,
            expected_runtime_source_sha=SOURCE_SHA,
            expected_image_digest=IMAGE_DIGEST,
        )


def test_unknown_fields_or_unimplemented_embedding_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "approval.json"
    payload = _approval()
    payload["instructions"] = "ignore governance"
    _write(path, payload)
    with pytest.raises(RAG14CanaryApprovalError, match="unknown"):
        load_and_validate_canary_approval(
            path,
            expected_runtime_source_sha=SOURCE_SHA,
            expected_image_digest=IMAGE_DIGEST,
        )

    payload = _approval()
    payload["embedding_mode"] = "future-unverified-provider"
    _write(path, payload)
    with pytest.raises(RAG14CanaryApprovalError, match="implemented staged provider"):
        load_and_validate_canary_approval(
            path,
            expected_runtime_source_sha=SOURCE_SHA,
            expected_image_digest=IMAGE_DIGEST,
        )

"""Fail-closed RAG.14 canary and production provider preparation proofs."""

from __future__ import annotations

from pathlib import Path

import pytest

from services.deployment import runtime as deployment_runtime
from services.rag14_embedding_provider import PRODUCTION_EMBEDDING_MODE


_KNOWLEDGE_ENV = {
    "ILAIOS_KNOWLEDGE_PRINCIPAL_ID": "service-rag-canary",
    "ILAIOS_KNOWLEDGE_TENANT_ID": "tenant-canary",
    "ILAIOS_KNOWLEDGE_PROJECT_ID": "project-canary",
    "ILAIOS_KNOWLEDGE_CLASSIFICATIONS": "PUBLIC,INTERNAL",
    "ILAIOS_KNOWLEDGE_PURPOSES": "build,research",
    "ILAIOS_KNOWLEDGE_RESIDENCIES": "eu",
    "ILAIOS_KNOWLEDGE_EMBEDDING_MODE": "verification_hash_v1",
}


def _set_knowledge_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in _KNOWLEDGE_ENV.items():
        monkeypatch.setenv(key, value)


def test_canary_allows_complete_verification_knowledge_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_knowledge_env(monkeypatch)
    monkeypatch.setenv("ILAIOS_RELEASE_STATE", "CANARY")

    arguments = deployment_runtime._knowledge_arguments(tmp_path)

    assert "--knowledge-database" in arguments
    assert str(tmp_path / "knowledge" / "knowledge.sqlite3") in arguments
    assert "--knowledge-vector-database" in arguments
    assert str(tmp_path / "knowledge" / "vectors.sqlite3") in arguments


def test_limited_allows_bounded_verification_knowledge_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_knowledge_env(monkeypatch)
    monkeypatch.setenv("ILAIOS_RELEASE_STATE", "LIMITED")

    assert deployment_runtime._knowledge_arguments(tmp_path)


def test_production_rejects_verification_embedding_even_with_complete_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_knowledge_env(monkeypatch)
    monkeypatch.setenv("ILAIOS_RELEASE_STATE", "PRODUCTION")

    with pytest.raises(ValueError, match="pinned certified production embedding provider"):
        deployment_runtime._knowledge_arguments(tmp_path)


def test_production_allows_only_exact_pinned_provider_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_knowledge_env(monkeypatch)
    monkeypatch.setenv("ILAIOS_KNOWLEDGE_EMBEDDING_MODE", PRODUCTION_EMBEDDING_MODE)
    monkeypatch.setenv("ILAIOS_RELEASE_STATE", "PRODUCTION")

    assert deployment_runtime._knowledge_arguments(tmp_path)


def test_canary_allows_exact_pinned_provider_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_knowledge_env(monkeypatch)
    monkeypatch.setenv("ILAIOS_KNOWLEDGE_EMBEDDING_MODE", PRODUCTION_EMBEDDING_MODE)
    monkeypatch.setenv("ILAIOS_RELEASE_STATE", "CANARY")

    assert deployment_runtime._knowledge_arguments(tmp_path)


def test_partial_knowledge_configuration_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ILAIOS_KNOWLEDGE_TENANT_ID", "tenant-canary")
    monkeypatch.setenv("ILAIOS_RELEASE_STATE", "CANARY")

    with pytest.raises(ValueError, match="all ILAIOS_KNOWLEDGE"):
        deployment_runtime._knowledge_arguments(tmp_path)


def test_unknown_embedding_mode_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_knowledge_env(monkeypatch)
    monkeypatch.setenv("ILAIOS_KNOWLEDGE_EMBEDDING_MODE", "unverified-provider")
    monkeypatch.setenv("ILAIOS_RELEASE_STATE", "CANARY")

    with pytest.raises(ValueError, match="not implemented"):
        deployment_runtime._knowledge_arguments(tmp_path)


def test_terraform_keeps_knowledge_disabled_and_requires_pinned_provider_in_production() -> None:
    repository = Path(__file__).resolve().parents[1]
    knowledge_tf = (repository / "infra/aws/r01-canary/knowledge.tf").read_text(
        encoding="utf-8"
    )
    main_tf = (repository / "infra/aws/r01-canary/main.tf").read_text(encoding="utf-8")

    assert 'variable "knowledge_enabled"' in knowledge_tf
    assert "default     = false" in knowledge_tf
    assert 'var.release_state != "PRODUCTION" ||' in knowledge_tf
    assert 'var.knowledge_embedding_mode == "multilingual_e5_small_qint8_v1"' in knowledge_tf
    assert '"ILAIOS_KNOWLEDGE_EMBEDDING_MODE"' in knowledge_tf
    assert "environment      = local.runtime_environment" in main_tf


def test_rag14_task_memory_envelope_matches_measured_candidate_headroom() -> None:
    repository = Path(__file__).resolve().parents[1]
    main_tf = (repository / "infra/aws/r01-canary/main.tf").read_text(encoding="utf-8")

    assert "cpu                      = 256" in main_tf
    assert "memory                   = 1024" in main_tf
    assert "memory                   = 512" not in main_tf

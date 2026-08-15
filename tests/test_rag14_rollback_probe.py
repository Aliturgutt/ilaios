"""The RAG.14 rollback drill must fail a bounded task revision and restore truth."""

from __future__ import annotations

from pathlib import Path

from services.rag14_rollback_probe import _BAD_MODE, _bad_registration


def test_bad_registration_changes_only_embedding_mode_in_runtime_environment() -> None:
    current = {
        "family": "ilaios-r01-canary",
        "cpu": "256",
        "memory": "1024",
        "containerDefinitions": [
            {
                "name": "runtime",
                "image": "repo@sha256:" + ("a" * 64),
                "environment": [
                    {"name": "ILAIOS_RELEASE_STATE", "value": "CANARY"},
                    {
                        "name": "ILAIOS_KNOWLEDGE_EMBEDDING_MODE",
                        "value": "multilingual_e5_small_qint8_v1",
                    },
                ],
            }
        ],
    }

    bad = _bad_registration(current)

    assert bad["cpu"] == "256"
    assert bad["memory"] == "1024"
    container = bad["containerDefinitions"][0]
    assert container["image"] == current["containerDefinitions"][0]["image"]
    environment = {item["name"]: item["value"] for item in container["environment"]}
    assert environment["ILAIOS_RELEASE_STATE"] == "CANARY"
    assert environment["ILAIOS_KNOWLEDGE_EMBEDDING_MODE"] == _BAD_MODE
    original_environment = {
        item["name"]: item["value"]
        for item in current["containerDefinitions"][0]["environment"]
    }
    assert original_environment["ILAIOS_KNOWLEDGE_EMBEDDING_MODE"] == (
        "multilingual_e5_small_qint8_v1"
    )


def test_rollback_probe_source_requires_bad_failure_and_explicit_restore() -> None:
    repository = Path(__file__).resolve().parents[1]
    source = (repository / "services/rag14_rollback_probe.py").read_text(
        encoding="utf-8"
    )

    assert "register-task-definition" in source
    assert "configured Knowledge embedding mode is unknown" in source
    assert "finally:" in source
    assert "_update_service(current_arn)" in source
    assert '"bad_deployment_simulated": True' in source
    assert '"rollback_to_verified_artifact": True' in source
    assert '"production_authority": False' in source

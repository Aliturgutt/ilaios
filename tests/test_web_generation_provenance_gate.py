from __future__ import annotations

import pytest

from services.web_generation_provenance_gate import (
    WebGenerationProvenanceError,
    evaluate_web_generation_provenance,
)


def _evidence(*, mode: str = "CREATE") -> dict[str, object]:
    return {
        "mode": mode,
        "execution_id": "exec-web-001",
        "tenant_id": "tenant-001",
        "prompt_spec_sha256": "a" * 64,
        "generator_version": "web-generator@1.0.0",
        "worker_version": "web-worker@1.0.0",
        "skill_versions": ["ilaios-web-design@1", "ilaios-web-validation@1"],
        "dependency_lock_sha256": "b" * 64,
        "input_source_sha256": "c" * 64 if mode == "REVISE" else None,
        "generated_source_sha256": "d" * 64,
        "build_artifact_sha256": "e" * 64,
        "qa_evidence_sha256": ["f" * 64, "1" * 64],
        "component_provenance_sha256": ["2" * 64],
        "external_assets": [
            {
                "asset_id": "asset-hero-1",
                "sha256": "3" * 64,
                "license_id": "CC-BY-4.0",
                "source_ref": "https://example.invalid/asset/hero-1",
            }
        ],
    }


def test_create_provenance_passes_with_complete_immutable_evidence() -> None:
    verdict, receipt = evaluate_web_generation_provenance(_evidence())

    assert verdict == "PASS"
    assert receipt is not None
    assert receipt.mode == "CREATE"
    assert receipt.execution_id == "exec-web-001"
    assert receipt.generated_source_sha256 == "d" * 64
    assert receipt.build_artifact_sha256 == "e" * 64


def test_revise_requires_exact_input_source_sha() -> None:
    evidence = _evidence(mode="REVISE")
    evidence["input_source_sha256"] = None

    verdict, receipt = evaluate_web_generation_provenance(evidence)

    assert verdict == "FAIL"
    assert receipt is None


def test_empty_evidence_is_not_verified() -> None:
    assert evaluate_web_generation_provenance(None) == ("NOT_VERIFIED", None)
    assert evaluate_web_generation_provenance({}) == ("NOT_VERIFIED", None)


def test_cross_sha_source_mutation_invalidates_accepted_evidence() -> None:
    verdict, receipt = evaluate_web_generation_provenance(_evidence(mode="REVISE"))
    assert verdict == "PASS"
    assert receipt is not None

    with pytest.raises(WebGenerationProvenanceError, match="generated source changed"):
        receipt.validate_currentness(
            generated_source_sha256="9" * 64,
            dependency_lock_sha256="b" * 64,
            input_source_sha256="c" * 64,
        )


def test_dependency_lock_mutation_invalidates_accepted_evidence() -> None:
    verdict, receipt = evaluate_web_generation_provenance(_evidence())
    assert verdict == "PASS"
    assert receipt is not None

    with pytest.raises(WebGenerationProvenanceError, match="dependency lock changed"):
        receipt.validate_currentness(
            generated_source_sha256="d" * 64,
            dependency_lock_sha256="8" * 64,
        )


def test_revise_input_mutation_invalidates_accepted_evidence() -> None:
    verdict, receipt = evaluate_web_generation_provenance(_evidence(mode="REVISE"))
    assert verdict == "PASS"
    assert receipt is not None

    with pytest.raises(WebGenerationProvenanceError, match="input source changed"):
        receipt.validate_currentness(
            generated_source_sha256="d" * 64,
            dependency_lock_sha256="b" * 64,
            input_source_sha256="7" * 64,
        )


def test_deployment_identity_is_bound_as_an_atomic_pair() -> None:
    evidence = _evidence()
    evidence["deployment_environment"] = "production"

    verdict, receipt = evaluate_web_generation_provenance(evidence)

    assert verdict == "FAIL"
    assert receipt is None


def test_external_asset_reuse_requires_license_and_source_provenance() -> None:
    evidence = _evidence()
    evidence["external_assets"] = [
        {
            "asset_id": "asset-hero-1",
            "sha256": "3" * 64,
            "license_id": "",
            "source_ref": "https://example.invalid/asset/hero-1",
        }
    ]

    verdict, receipt = evaluate_web_generation_provenance(evidence)

    assert verdict == "FAIL"
    assert receipt is None


def test_malformed_digest_fails_closed() -> None:
    evidence = _evidence()
    evidence["build_artifact_sha256"] = "ABC"

    verdict, receipt = evaluate_web_generation_provenance(evidence)

    assert verdict == "FAIL"
    assert receipt is None

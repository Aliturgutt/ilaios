from __future__ import annotations

from services.integrations.web_generation_provenance_binding import (
    evaluate_web_manifest_provenance,
)


def _sha(char: str) -> str:
    return char * 64


def _accepted_manifest(*, mode: str = "CREATE") -> dict[str, object]:
    return {
        "accepted": True,
        "finalization_status": "accepted",
        "generation_mode": mode,
        "job_id": "job-web-123",
        "tenant_id": "tenant-123",
        "spec_hash": _sha("a"),
        "generator_version": "web.factory.v1",
        "worker_version": "worker-web.v1",
        "skill_versions": ["ilaios-web-architecture@1", "ilaios-web-validation@1"],
        "dependency_lock_sha256": _sha("b"),
        "input_source_sha256": None,
        "source_project_digest": _sha("c"),
        "artifact_digest": _sha("d"),
        "qa_evidence_sha256": [_sha("e"), _sha("f")],
        "component_provenance_sha256": [_sha("1")],
        "external_asset_provenance": [],
        "deployment_environment": None,
        "deployment_identity": None,
    }


def test_absent_or_unaccepted_manifest_is_not_verified() -> None:
    assert evaluate_web_manifest_provenance(None) == ("NOT_VERIFIED", None)
    assert evaluate_web_manifest_provenance({}) == ("NOT_VERIFIED", None)
    assert evaluate_web_manifest_provenance({"accepted": False}) == (
        "NOT_VERIFIED",
        None,
    )


def test_accepted_manifest_requires_complete_runtime_provenance() -> None:
    manifest = _accepted_manifest()
    manifest.pop("dependency_lock_sha256")
    verdict, receipt = evaluate_web_manifest_provenance(manifest)
    assert verdict == "FAIL"
    assert receipt is None


def test_create_manifest_binds_exact_runtime_lineage() -> None:
    manifest = _accepted_manifest()
    verdict, receipt = evaluate_web_manifest_provenance(manifest)
    assert verdict == "PASS"
    assert receipt is not None
    assert receipt.execution_id == manifest["job_id"]
    assert receipt.tenant_id == manifest["tenant_id"]
    assert receipt.prompt_spec_sha256 == manifest["spec_hash"]
    assert receipt.generated_source_sha256 == manifest["source_project_digest"]
    assert receipt.build_artifact_sha256 == manifest["artifact_digest"]


def test_revise_manifest_requires_exact_input_source() -> None:
    manifest = _accepted_manifest(mode="REVISE")
    verdict, receipt = evaluate_web_manifest_provenance(manifest)
    assert verdict == "FAIL"
    assert receipt is None

    manifest["input_source_sha256"] = _sha("9")
    verdict, receipt = evaluate_web_manifest_provenance(manifest)
    assert verdict == "PASS"
    assert receipt is not None
    assert receipt.input_source_sha256 == _sha("9")


def test_malformed_deployment_binding_fails_closed() -> None:
    manifest = _accepted_manifest()
    manifest["deployment_environment"] = "production"
    verdict, receipt = evaluate_web_manifest_provenance(manifest)
    assert verdict == "FAIL"
    assert receipt is None


def test_external_asset_requires_license_and_source_provenance() -> None:
    manifest = _accepted_manifest()
    manifest["external_asset_provenance"] = [
        {
            "asset_id": "asset-1",
            "sha256": _sha("7"),
            "license_id": "",
            "source_ref": "https://example.invalid/asset",
        }
    ]
    verdict, receipt = evaluate_web_manifest_provenance(manifest)
    assert verdict == "FAIL"
    assert receipt is None

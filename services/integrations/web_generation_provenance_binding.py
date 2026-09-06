"""Bind canonical accepted Web manifests to generation provenance validation.

This module does not create a second Evidence or Web Factory authority. It only
projects already-persisted canonical Web runtime evidence into the fail-closed
generation-provenance acceptance gate.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Literal, cast

from services.web_generation_provenance_gate import (
    WebGenerationProvenanceReceipt,
    evaluate_web_generation_provenance,
)


ProvenanceVerdict = Literal["PASS", "FAIL", "NOT_VERIFIED"]


def evaluate_web_manifest_provenance(
    manifest: Mapping[str, object] | None,
) -> tuple[ProvenanceVerdict, WebGenerationProvenanceReceipt | None]:
    """Validate an accepted canonical Web manifest against provenance requirements.

    An absent manifest is NOT_VERIFIED. Once an accepted manifest exists, missing,
    malformed, stale, or cross-lineage provenance fails closed.
    """
    if manifest is None or not manifest:
        return "NOT_VERIFIED", None
    if manifest.get("accepted") is not True or manifest.get("finalization_status") != "accepted":
        return "NOT_VERIFIED", None

    evidence = _project_provenance_evidence(manifest)
    verdict, receipt = evaluate_web_generation_provenance(evidence)
    if verdict != "PASS" or receipt is None:
        return "FAIL", None

    source_digest = _text(manifest, "source_project_digest")
    dependency_lock = _text(manifest, "dependency_lock_sha256")
    input_source = _optional_text(manifest, "input_source_sha256")
    try:
        receipt.validate_currentness(
            generated_source_sha256=source_digest,
            dependency_lock_sha256=dependency_lock,
            input_source_sha256=input_source,
        )
    except ValueError:
        return "FAIL", None

    if receipt.execution_id != _text(manifest, "job_id"):
        return "FAIL", None
    if receipt.tenant_id != _text(manifest, "tenant_id"):
        return "FAIL", None
    if receipt.prompt_spec_sha256 != _text(manifest, "spec_hash"):
        return "FAIL", None
    if receipt.generated_source_sha256 != source_digest:
        return "FAIL", None
    if receipt.build_artifact_sha256 != _text(manifest, "artifact_digest"):
        return "FAIL", None
    return "PASS", receipt


def _project_provenance_evidence(manifest: Mapping[str, object]) -> dict[str, object]:
    return {
        "mode": _text(manifest, "generation_mode"),
        "execution_id": _text(manifest, "job_id"),
        "tenant_id": _text(manifest, "tenant_id"),
        "prompt_spec_sha256": _text(manifest, "spec_hash"),
        "generator_version": _text(manifest, "generator_version"),
        "worker_version": _text(manifest, "worker_version"),
        "skill_versions": list(_text_sequence(manifest, "skill_versions")),
        "dependency_lock_sha256": _text(manifest, "dependency_lock_sha256"),
        "input_source_sha256": _optional_text(manifest, "input_source_sha256"),
        "generated_source_sha256": _text(manifest, "source_project_digest"),
        "build_artifact_sha256": _text(manifest, "artifact_digest"),
        "qa_evidence_sha256": list(_text_sequence(manifest, "qa_evidence_sha256")),
        "component_provenance_sha256": list(
            _optional_text_sequence(manifest, "component_provenance_sha256")
        ),
        "external_assets": list(_mapping_sequence(manifest, "external_asset_provenance")),
        "deployment_environment": _optional_text(manifest, "deployment_environment"),
        "deployment_identity": _optional_text(manifest, "deployment_identity"),
    }


def _text(manifest: Mapping[str, object], key: str) -> str:
    value = manifest.get(key)
    if not isinstance(value, str) or not value:
        return ""
    return value


def _optional_text(manifest: Mapping[str, object], key: str) -> str | None:
    value = manifest.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        return ""
    return value


def _text_sequence(manifest: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = manifest.get(key)
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return ()
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            return ()
        result.append(item)
    return tuple(result)


def _optional_text_sequence(manifest: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = manifest.get(key)
    if value is None:
        return ()
    return _text_sequence(manifest, key)


def _mapping_sequence(
    manifest: Mapping[str, object], key: str
) -> tuple[Mapping[str, object], ...]:
    value = manifest.get(key)
    if value is None:
        return ()
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return ()
    result: list[Mapping[str, object]] = []
    for item in value:
        if not isinstance(item, Mapping):
            return ()
        result.append(cast(Mapping[str, object], item))
    return tuple(result)

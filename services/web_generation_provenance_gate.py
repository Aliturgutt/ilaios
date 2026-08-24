"""Fail-closed acceptance gate for Web Factory generation provenance receipts.

This module validates evidence produced by the existing Web Factory/runtime/evidence
path. It does not generate code, persist credentials, deploy artifacts, or replace
the canonical Evidence authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Mapping, Sequence


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


class WebGenerationProvenanceError(ValueError):
    """The supplied provenance is missing, malformed, stale, or cross-lineage."""


@dataclass(frozen=True, slots=True)
class ExternalAssetProvenance:
    asset_id: str
    sha256: str
    license_id: str
    source_ref: str


@dataclass(frozen=True, slots=True)
class WebGenerationProvenanceReceipt:
    mode: Literal["CREATE", "REVISE"]
    execution_id: str
    tenant_id: str
    prompt_spec_sha256: str
    generator_version: str
    worker_version: str
    skill_versions: tuple[str, ...]
    dependency_lock_sha256: str
    input_source_sha256: str | None
    generated_source_sha256: str
    build_artifact_sha256: str
    qa_evidence_sha256: tuple[str, ...]
    component_provenance_sha256: tuple[str, ...] = ()
    external_assets: tuple[ExternalAssetProvenance, ...] = ()
    deployment_environment: str | None = None
    deployment_identity: str | None = None

    def validate_currentness(
        self,
        *,
        generated_source_sha256: str,
        dependency_lock_sha256: str,
        input_source_sha256: str | None = None,
    ) -> None:
        """Reject stale evidence after source, dependency, or REVISE-input mutation."""
        _require_sha(generated_source_sha256, "current generated source SHA")
        _require_sha(dependency_lock_sha256, "current dependency lock SHA")
        if generated_source_sha256 != self.generated_source_sha256:
            raise WebGenerationProvenanceError("generated source changed after provenance acceptance")
        if dependency_lock_sha256 != self.dependency_lock_sha256:
            raise WebGenerationProvenanceError("dependency lock changed after provenance acceptance")
        if self.mode == "REVISE":
            if input_source_sha256 is None:
                raise WebGenerationProvenanceError("REVISE currentness requires input source SHA")
            _require_sha(input_source_sha256, "current input source SHA")
            if input_source_sha256 != self.input_source_sha256:
                raise WebGenerationProvenanceError("REVISE input source changed after provenance acceptance")


def evaluate_web_generation_provenance(
    evidence: Mapping[str, object] | None,
) -> tuple[Literal["PASS", "FAIL", "NOT_VERIFIED"], WebGenerationProvenanceReceipt | None]:
    """Return an evidence-only verdict; malformed supplied evidence fails closed."""
    if evidence is None or not evidence:
        return "NOT_VERIFIED", None
    try:
        return "PASS", _parse_receipt(evidence)
    except WebGenerationProvenanceError:
        return "FAIL", None


def _parse_receipt(evidence: Mapping[str, object]) -> WebGenerationProvenanceReceipt:
    mode = _required_text(evidence, "mode")
    if mode not in {"CREATE", "REVISE"}:
        raise WebGenerationProvenanceError("unsupported generation mode")

    execution_id = _required_id(evidence, "execution_id")
    tenant_id = _required_id(evidence, "tenant_id")
    prompt_spec_sha256 = _required_sha(evidence, "prompt_spec_sha256")
    generator_version = _required_text(evidence, "generator_version")
    worker_version = _required_text(evidence, "worker_version")
    skill_versions = _required_text_tuple(evidence, "skill_versions")
    dependency_lock_sha256 = _required_sha(evidence, "dependency_lock_sha256")
    generated_source_sha256 = _required_sha(evidence, "generated_source_sha256")
    build_artifact_sha256 = _required_sha(evidence, "build_artifact_sha256")
    qa_evidence_sha256 = _required_sha_tuple(evidence, "qa_evidence_sha256")
    component_provenance_sha256 = _optional_sha_tuple(evidence, "component_provenance_sha256")

    input_value = evidence.get("input_source_sha256")
    input_source_sha256: str | None
    if input_value is None:
        input_source_sha256 = None
    elif isinstance(input_value, str):
        _require_sha(input_value, "input_source_sha256")
        input_source_sha256 = input_value
    else:
        raise WebGenerationProvenanceError("input_source_sha256 must be a SHA-256 string or null")
    if mode == "REVISE" and input_source_sha256 is None:
        raise WebGenerationProvenanceError("REVISE provenance requires exact input source SHA")

    assets = _parse_external_assets(evidence.get("external_assets", ()))
    deployment_environment = _optional_text(evidence, "deployment_environment")
    deployment_identity = _optional_text(evidence, "deployment_identity")
    if (deployment_environment is None) != (deployment_identity is None):
        raise WebGenerationProvenanceError(
            "deployment environment and identity must be supplied together"
        )

    return WebGenerationProvenanceReceipt(
        mode=mode,  # type: ignore[arg-type]
        execution_id=execution_id,
        tenant_id=tenant_id,
        prompt_spec_sha256=prompt_spec_sha256,
        generator_version=generator_version,
        worker_version=worker_version,
        skill_versions=skill_versions,
        dependency_lock_sha256=dependency_lock_sha256,
        input_source_sha256=input_source_sha256,
        generated_source_sha256=generated_source_sha256,
        build_artifact_sha256=build_artifact_sha256,
        qa_evidence_sha256=qa_evidence_sha256,
        component_provenance_sha256=component_provenance_sha256,
        external_assets=assets,
        deployment_environment=deployment_environment,
        deployment_identity=deployment_identity,
    )


def _required_text(evidence: Mapping[str, object], key: str) -> str:
    value = evidence.get(key)
    if not isinstance(value, str) or not value or value != value.strip():
        raise WebGenerationProvenanceError(f"{key} must be non-blank and trimmed")
    return value


def _optional_text(evidence: Mapping[str, object], key: str) -> str | None:
    value = evidence.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value or value != value.strip():
        raise WebGenerationProvenanceError(f"{key} must be non-blank and trimmed when supplied")
    return value


def _required_id(evidence: Mapping[str, object], key: str) -> str:
    value = _required_text(evidence, key)
    if not _ID.fullmatch(value):
        raise WebGenerationProvenanceError(f"{key} has an invalid identifier format")
    return value


def _required_sha(evidence: Mapping[str, object], key: str) -> str:
    value = _required_text(evidence, key)
    _require_sha(value, key)
    return value


def _require_sha(value: str, field: str) -> None:
    if not _SHA256.fullmatch(value):
        raise WebGenerationProvenanceError(f"{field} must be a lowercase SHA-256 digest")


def _required_text_tuple(evidence: Mapping[str, object], key: str) -> tuple[str, ...]:
    values = _sequence(evidence.get(key), key)
    if not values:
        raise WebGenerationProvenanceError(f"{key} must contain at least one item")
    result: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value or value != value.strip():
            raise WebGenerationProvenanceError(f"{key} contains an invalid text item")
        result.append(value)
    if len(set(result)) != len(result):
        raise WebGenerationProvenanceError(f"{key} contains duplicate items")
    return tuple(result)


def _required_sha_tuple(evidence: Mapping[str, object], key: str) -> tuple[str, ...]:
    values = _optional_sha_tuple(evidence, key)
    if not values:
        raise WebGenerationProvenanceError(f"{key} must contain at least one evidence digest")
    return values


def _optional_sha_tuple(evidence: Mapping[str, object], key: str) -> tuple[str, ...]:
    raw = evidence.get(key, ())
    values = _sequence(raw, key)
    result: list[str] = []
    for value in values:
        if not isinstance(value, str):
            raise WebGenerationProvenanceError(f"{key} contains a non-string digest")
        _require_sha(value, key)
        result.append(value)
    if len(set(result)) != len(result):
        raise WebGenerationProvenanceError(f"{key} contains duplicate digests")
    return tuple(result)


def _parse_external_assets(raw: object) -> tuple[ExternalAssetProvenance, ...]:
    values = _sequence(raw, "external_assets")
    assets: list[ExternalAssetProvenance] = []
    for item in values:
        if not isinstance(item, Mapping):
            raise WebGenerationProvenanceError("external asset provenance must be an object")
        asset_id = _required_id(item, "asset_id")
        sha256 = _required_sha(item, "sha256")
        license_id = _required_text(item, "license_id")
        source_ref = _required_text(item, "source_ref")
        assets.append(ExternalAssetProvenance(asset_id, sha256, license_id, source_ref))
    if len({item.asset_id for item in assets}) != len(assets):
        raise WebGenerationProvenanceError("external asset provenance contains duplicate asset IDs")
    return tuple(assets)


def _sequence(value: object, field: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise WebGenerationProvenanceError(f"{field} must be an array")
    return value

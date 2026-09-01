"""Validate a fresh, explicit RAG.14 canary approval without mutating infrastructure."""

from __future__ import annotations

import hashlib
import ipaddress
import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from services.rag14_embedding_provider import (
    PRODUCTION_EMBEDDING_MODE,
    VERIFICATION_EMBEDDING_MODE,
)


class RAG14CanaryApprovalError(ValueError):
    """The canary approval is absent, stale for the release, or malformed."""


@dataclass(frozen=True, slots=True)
class RAG14CanaryApproval:
    runtime_source_sha: str
    image_digest: str
    canary_ipv4_cidr: str
    canary_tenant_id: str
    canary_project_id: str
    knowledge_principal_id: str
    classifications: tuple[str, ...]
    purposes: tuple[str, ...]
    residencies: tuple[str, ...]
    embedding_mode: str
    external_spend_approval: bool
    evidence_sha256: str

    def terraform_environment(self) -> dict[str, str]:
        """Return only non-secret staged Terraform values after validation."""
        return {
            "TF_VAR_enable_canary": "true",
            "TF_VAR_release_state": "CANARY",
            "TF_VAR_desired_count": "1",
            "TF_VAR_image_digest": self.image_digest,
            "TF_VAR_canary_ipv4_cidrs": json.dumps([self.canary_ipv4_cidr]),
            "TF_VAR_knowledge_enabled": "true",
            "TF_VAR_knowledge_embedding_mode": self.embedding_mode,
            "TF_VAR_knowledge_principal_id": self.knowledge_principal_id,
            "TF_VAR_knowledge_tenant_id": self.canary_tenant_id,
            "TF_VAR_knowledge_project_id": self.canary_project_id,
            "TF_VAR_knowledge_classifications": json.dumps(self.classifications),
            "TF_VAR_knowledge_purposes": json.dumps(self.purposes),
            "TF_VAR_knowledge_residencies": json.dumps(self.residencies),
        }


def load_and_validate_canary_approval(
    path: Path,
    *,
    expected_runtime_source_sha: str,
    expected_image_digest: str,
) -> RAG14CanaryApproval:
    if not path.is_file() or path.is_symlink():
        raise RAG14CanaryApprovalError("fresh RAG.14 canary approval file is required")
    raw: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise RAG14CanaryApprovalError("RAG.14 canary approval must be a JSON object")
    data = cast(dict[str, object], raw)
    allowed = {
        "approval",
        "external_spend_approval",
        "runtime_source_sha",
        "image_digest",
        "canary_ipv4_cidr",
        "canary_tenant_id",
        "canary_project_id",
        "knowledge_principal_id",
        "classifications",
        "purposes",
        "residencies",
        "embedding_mode",
    }
    if set(data) != allowed:
        raise RAG14CanaryApprovalError("RAG.14 canary approval fields are incomplete or unknown")
    if data.get("approval") != "RAG.14 CANARY EVIDENCE APPROVED":
        raise RAG14CanaryApprovalError("explicit RAG.14 canary approval is missing")
    if data.get("external_spend_approval") is not True:
        raise RAG14CanaryApprovalError("fresh external-spend approval is missing")

    runtime_source_sha = _sha40(data.get("runtime_source_sha"), "runtime_source_sha")
    if runtime_source_sha != expected_runtime_source_sha:
        raise RAG14CanaryApprovalError("approval does not bind the expected runtime source SHA")
    image_digest = _image_digest(data.get("image_digest"))
    if image_digest != expected_image_digest:
        raise RAG14CanaryApprovalError("approval does not bind the expected immutable image digest")

    cidr_value = _string(data.get("canary_ipv4_cidr"), "canary_ipv4_cidr")
    try:
        network = ipaddress.ip_network(cidr_value, strict=True)
    except ValueError as error:
        raise RAG14CanaryApprovalError("canary source allowlist is invalid") from error
    if network.version != 4 or network.prefixlen != 32:
        raise RAG14CanaryApprovalError("canary source allowlist must be one IPv4 /32")

    tenant = _string(data.get("canary_tenant_id"), "canary_tenant_id")
    project = _string(data.get("canary_project_id"), "canary_project_id")
    principal = _string(data.get("knowledge_principal_id"), "knowledge_principal_id")
    classifications = _string_tuple(data.get("classifications"), "classifications")
    purposes = _string_tuple(data.get("purposes"), "purposes")
    residencies = _string_tuple(data.get("residencies"), "residencies")
    embedding_mode = _string(data.get("embedding_mode"), "embedding_mode")
    if embedding_mode not in {VERIFICATION_EMBEDDING_MODE, PRODUCTION_EMBEDDING_MODE}:
        raise RAG14CanaryApprovalError("embedding mode is not an implemented staged provider")

    evidence_material = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return RAG14CanaryApproval(
        runtime_source_sha=runtime_source_sha,
        image_digest=image_digest,
        canary_ipv4_cidr=str(network),
        canary_tenant_id=tenant,
        canary_project_id=project,
        knowledge_principal_id=principal,
        classifications=classifications,
        purposes=purposes,
        residencies=residencies,
        embedding_mode=embedding_mode,
        external_spend_approval=True,
        evidence_sha256=hashlib.sha256(evidence_material.encode("utf-8")).hexdigest(),
    )


def _string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise RAG14CanaryApprovalError(f"{name} must be a non-empty trimmed string")
    if len(value) > 128:
        raise RAG14CanaryApprovalError(f"{name} exceeds bounded length")
    return value


def _string_tuple(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise RAG14CanaryApprovalError(f"{name} must be a non-empty string array")
    result: list[str] = []
    for item in value:
        result.append(_string(item, name))
    if len(result) != len(set(result)):
        raise RAG14CanaryApprovalError(f"{name} must not contain duplicates")
    return tuple(result)


def _sha40(value: object, name: str) -> str:
    text = _string(value, name)
    if len(text) != 40 or any(character not in "0123456789abcdef" for character in text):
        raise RAG14CanaryApprovalError(f"{name} must be a lowercase 40-character Git SHA")
    return text


def _image_digest(value: object) -> str:
    text = _string(value, "image_digest")
    prefix = "sha256:"
    digest = text.removeprefix(prefix)
    if not text.startswith(prefix) or len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise RAG14CanaryApprovalError("image_digest must be an immutable sha256 digest")
    return text

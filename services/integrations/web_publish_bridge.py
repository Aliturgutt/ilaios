"""Bridge accepted DurableWebProductRuntime manifests into Web publish input."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from .web_delivery import tree_sha256
from .web_publish_runtime import AcceptedWebArtifact, WebPublishError


def accepted_artifact_from_manifest(
    manifest: Mapping[str, object],
) -> AcceptedWebArtifact:
    """Fail closed unless the canonical Web finished-product manifest is accepted."""
    if manifest.get("adapter_id") != "web.product-runtime.v1":
        raise WebPublishError("Web publish manifest adapter identity is invalid")
    if manifest.get("accepted") is not True:
        raise WebPublishError("Web publish manifest is not accepted")
    if manifest.get("finalization_status") != "accepted":
        raise WebPublishError("Web publish finalization is not accepted")
    if manifest.get("job_state_proven") is not True:
        raise WebPublishError("Web publish job completion is not proven")
    if manifest.get("admission_proven") is not True or manifest.get("grant_proven") is not True:
        raise WebPublishError("Web publish governance evidence is incomplete")
    if manifest.get("deployment_state") != "NOT_DEPLOYED":
        raise WebPublishError("Web publish manifest is not in NOT_DEPLOYED state")
    if manifest.get("deployment_contract") != "web.deployment-receipt.v1":
        raise WebPublishError("Web publish deployment contract is incompatible")
    if manifest.get("source_commit_bound") is not True:
        raise WebPublishError("Web publish source commit is not bound")

    site_id = _required(manifest, "site_id")
    tenant_id = _required(manifest, "tenant_id")
    source_commit_sha = _required(manifest, "source_commit_sha")
    source_project_path = Path(_required(manifest, "source_project_path"))
    source_project_digest = _required(manifest, "source_project_digest")

    if not source_project_path.is_dir():
        raise WebPublishError("Web publish source project path is missing")
    actual = tree_sha256(source_project_path)
    if actual != source_project_digest:
        raise WebPublishError("Web publish source project digest mismatch")

    return AcceptedWebArtifact(
        site_id=site_id,
        tenant_id=tenant_id,
        project_root=source_project_path,
        source_commit_sha=source_commit_sha,
        artifact_sha256=actual,
        acceptance_proven=True,
    )


def _required(manifest: Mapping[str, object], key: str) -> str:
    value = manifest.get(key)
    if not isinstance(value, str) or not value.strip():
        raise WebPublishError(f"Web publish manifest field {key} is missing")
    return value.strip()


__all__ = ["accepted_artifact_from_manifest"]

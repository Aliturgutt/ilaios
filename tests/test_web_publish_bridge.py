from pathlib import Path

import pytest

from services.integrations.web_delivery import tree_sha256
from services.integrations.web_publish_bridge import accepted_artifact_from_manifest
from services.integrations.web_publish_runtime import WebPublishError


def _manifest(root: Path) -> dict[str, object]:
    return {
        "adapter_id": "web.product-runtime.v1",
        "accepted": True,
        "finalization_status": "accepted",
        "job_state_proven": True,
        "admission_proven": True,
        "grant_proven": True,
        "deployment_state": "NOT_DEPLOYED",
        "deployment_contract": "web.deployment-receipt.v1",
        "source_commit_bound": True,
        "site_id": "site-1",
        "tenant_id": "tenant-1",
        "source_commit_sha": "a" * 40,
        "source_project_path": str(root),
        "source_project_digest": tree_sha256(root),
    }


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    (root / "package.json").write_text("{}\n", encoding="utf-8")
    return root


def test_accepted_web_manifest_becomes_publish_artifact(tmp_path: Path) -> None:
    root = _project(tmp_path)
    artifact = accepted_artifact_from_manifest(_manifest(root))
    assert artifact.site_id == "site-1"
    assert artifact.tenant_id == "tenant-1"
    assert artifact.artifact_sha256 == tree_sha256(root)
    assert artifact.acceptance_proven is True


def test_unaccepted_or_unbound_manifest_cannot_publish(tmp_path: Path) -> None:
    root = _project(tmp_path)
    manifest = _manifest(root)
    manifest["accepted"] = False
    with pytest.raises(WebPublishError, match="not accepted"):
        accepted_artifact_from_manifest(manifest)

    manifest = _manifest(root)
    manifest["source_commit_bound"] = False
    with pytest.raises(WebPublishError, match="source commit"):
        accepted_artifact_from_manifest(manifest)


def test_tampered_source_project_cannot_publish(tmp_path: Path) -> None:
    root = _project(tmp_path)
    manifest = _manifest(root)
    (root / "tampered.txt").write_text("changed", encoding="utf-8")
    with pytest.raises(WebPublishError, match="digest mismatch"):
        accepted_artifact_from_manifest(manifest)

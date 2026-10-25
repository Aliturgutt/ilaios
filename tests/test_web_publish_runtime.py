from pathlib import Path

import pytest

from services.integrations.web_delivery import WebDeploymentReceipt, tree_sha256
from services.integrations.web_publish_runtime import (
    AcceptedWebArtifact,
    WebPublishCoordinator,
    WebPublishError,
    WebPublishState,
    WebPublishStore,
    manual_domain_plan,
    verify_manual_domain,
)


class _Deployment:
    provider_id = "test.web-deployment.v1"

    def __init__(self) -> None:
        self.preview_calls = 0
        self.deploy_calls = 0

    def preview(self, project_root: Path, **kwargs: object) -> WebDeploymentReceipt:
        self.preview_calls += 1
        return _receipt(project_root, "preview-1", False, "https://preview.example.test")

    def deploy(self, project_root: Path, **kwargs: object) -> WebDeploymentReceipt:
        self.deploy_calls += 1
        return _receipt(project_root, "prod-1", True, "https://live.example.test")

    def rollback(self, deployment_id: str, **kwargs: object) -> WebDeploymentReceipt:
        raise AssertionError("rollback is not used in this slice")


class _Verifier:
    def __init__(self, result: bool = True) -> None:
        self.result = result

    def verify(self, url: str) -> bool:
        return self.result and url.startswith("https://")


class _Resolver:
    def __init__(self, cname: tuple[str, ...], txt: tuple[str, ...]) -> None:
        self._cname = cname
        self._txt = txt

    def cname(self, host: str) -> tuple[str, ...]:
        return self._cname

    def txt(self, host: str) -> tuple[str, ...]:
        return self._txt


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    (root / "package.json").write_text('{"scripts":{"build":"next build"}}\n', encoding="utf-8")
    return root


def _artifact(tmp_path: Path) -> AcceptedWebArtifact:
    root = _project(tmp_path)
    return AcceptedWebArtifact(
        site_id="site-1",
        tenant_id="tenant-1",
        project_root=root,
        source_commit_sha="a" * 40,
        artifact_sha256=tree_sha256(root),
        acceptance_proven=True,
    )


def _receipt(
    root: Path,
    deployment_id: str,
    production: bool,
    url: str,
) -> WebDeploymentReceipt:
    return WebDeploymentReceipt(
        contract="web.deployment-receipt.v1",
        provider="test.web-deployment.v1",
        deployment_id=deployment_id,
        source_commit_sha="a" * 40,
        artifact_sha256=tree_sha256(root),
        live_url=url,
        health="HEALTHY",
        rollback_reference=None,
        deployed_at="2026-09-04T00:00:00+00:00",
        public_production_proven=production,
    )


def test_preview_publish_history_is_durable_and_tenant_scoped(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path)
    store = WebPublishStore(tmp_path / "publish.db")
    deployment = _Deployment()
    coordinator = WebPublishCoordinator(store, deployment, _Verifier())

    preview = coordinator.preview(
        artifact,
        preview_authorization_proven=True,
        budget_proven=True,
    )
    assert preview.public_production_proven is False
    assert store.current_state("tenant-1", "site-1") is WebPublishState.PREVIEW_READY

    coordinator.request_publish(artifact, human_approval_required=True)
    assert store.current_state("tenant-1", "site-1") is WebPublishState.WAITING_APPROVAL

    production = coordinator.publish(
        artifact,
        authorization_proven=True,
        approval_proven=True,
        human_approval_required=True,
        budget_proven=True,
    )
    assert production.public_production_proven is True
    assert store.current_state("tenant-1", "site-1") is WebPublishState.LIVE
    states = [item["state"] for item in store.history("tenant-1", "site-1")]
    assert states == [
        "DRAFT",
        "PREVIEW_READY",
        "PUBLISH_REQUESTED",
        "WAITING_APPROVAL",
        "DEPLOYING",
        "VERIFYING",
        "LIVE",
    ]
    assert store.history("tenant-other", "site-1") == ()


def test_publish_fails_closed_without_required_approval(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path)
    store = WebPublishStore(tmp_path / "publish.db")
    deployment = _Deployment()
    coordinator = WebPublishCoordinator(store, deployment, _Verifier())
    coordinator.preview(artifact, preview_authorization_proven=True, budget_proven=True)
    coordinator.request_publish(artifact, human_approval_required=True)

    with pytest.raises(WebPublishError, match="approval"):
        coordinator.publish(
            artifact,
            authorization_proven=True,
            approval_proven=False,
            human_approval_required=True,
            budget_proven=True,
        )
    assert deployment.deploy_calls == 0


def test_preview_rejects_unaccepted_or_tampered_artifact(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path)
    (artifact.project_root / "unexpected.txt").write_text("tampered", encoding="utf-8")
    coordinator = WebPublishCoordinator(
        WebPublishStore(tmp_path / "publish.db"),
        _Deployment(),
        _Verifier(),
    )
    with pytest.raises(WebPublishError, match="digest"):
        coordinator.preview(
            artifact,
            preview_authorization_proven=True,
            budget_proven=True,
        )


def test_public_receipt_must_pass_independent_smoke_verification(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path)
    store = WebPublishStore(tmp_path / "publish.db")
    coordinator = WebPublishCoordinator(store, _Deployment(), _Verifier(False))
    with pytest.raises(WebPublishError, match="preview smoke"):
        coordinator.preview(
            artifact,
            preview_authorization_proven=True,
            budget_proven=True,
        )
    assert store.current_state("tenant-1", "site-1") is WebPublishState.FAILED


def test_manual_dns_plan_and_verification_are_fail_closed() -> None:
    plan = manual_domain_plan(
        "www.ornek.com",
        target_host="project-abc.ilaios.site",
        verification_token="verify_token_123456",
    )
    assert [(item.record_type, item.name) for item in plan.records] == [
        ("CNAME", "www"),
        ("TXT", "_ilaios-domain-verification"),
    ]
    verify_manual_domain(
        plan,
        _Resolver(("project-abc.ilaios.site",), ("verify_token_123456",)),
    )
    with pytest.raises(WebPublishError, match="CNAME"):
        verify_manual_domain(
            plan,
            _Resolver(("wrong.example",), ("verify_token_123456",)),
        )


def test_invalid_publish_transition_is_rejected(tmp_path: Path) -> None:
    store = WebPublishStore(tmp_path / "publish.db")
    store.ensure_draft("tenant-1", "site-1")
    with pytest.raises(WebPublishError, match="invalid Web publish transition"):
        store.transition("tenant-1", "site-1", WebPublishState.LIVE)

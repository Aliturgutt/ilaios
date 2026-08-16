"""Tests for the governed Vercel Web Factory deployment boundary."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

import pytest

from services.integrations.web_delivery import WebDeploymentError, tree_sha256
from services.integrations.web_vercel_delivery import VercelWebDeploymentAdapter


class _FakeVercelTransport:
    def __init__(
        self,
        responses: list[tuple[int, Mapping[str, object]]],
        *,
        probe_results: list[tuple[int, str]] | None = None,
    ) -> None:
        self.responses = deque(responses)
        self.calls: list[tuple[str, str, Mapping[str, object] | None]] = []
        self.probe_results = deque(probe_results or [])
        self.probes: list[str] = []

    def api(
        self,
        method: str,
        path: str,
        *,
        token: str,
        team_id: str,
        json_body: Mapping[str, object] | None = None,
    ) -> tuple[int, Mapping[str, object]]:
        assert token == "vercel-test-token"
        assert team_id == "team_test"
        self.calls.append((method, path, json_body))
        if not self.responses:
            raise AssertionError("unexpected Vercel API call")
        return self.responses.popleft()

    def probe(self, url: str) -> tuple[int, str]:
        self.probes.append(url)
        if not self.probe_results:
            raise AssertionError("unexpected Vercel health probe")
        return self.probe_results.popleft()


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "app").mkdir(parents=True)
    (root / "package.json").write_text(
        '{"scripts":{"build":"next build"},"dependencies":{"next":"16.2.11"}}\n',
        encoding="utf-8",
    )
    (root / "app/page.tsx").write_text(
        "export default function Page(){return <main>ILAIOS</main>}\n",
        encoding="utf-8",
    )
    return root


def _ready(
    *,
    deployment_id: str,
    source_sha: str,
    artifact_sha: str,
) -> dict[str, object]:
    return {
        "id": deployment_id,
        "readyState": "READY",
        "url": "generated-preview.vercel.app",
        "meta": {
            "ilaiosSourceCommitSha": source_sha,
            "ilaiosArtifactSha256": artifact_sha,
            "ilaiosDeploymentContract": "web.deployment-receipt.v1",
        },
    }


def _adapter(
    transport: _FakeVercelTransport,
    *,
    production_alias: str = "customer-site.vercel.app",
    max_inline_bytes: int = 8 * 1024 * 1024,
) -> VercelWebDeploymentAdapter:
    return VercelWebDeploymentAdapter(
        team_id="team_test",
        project_id="prj_test",
        project_name="ilaios-generated-test",
        production_alias=production_alias,
        credential_provider=lambda: "vercel-test-token",
        transport=transport,
        max_poll_attempts=3,
        poll_interval_seconds=0,
        max_inline_bytes=max_inline_bytes,
        sleeper=lambda _seconds: None,
    )


def test_vercel_deploy_is_preview_first_then_promotes_exact_expected_alias(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path)
    source_sha = "a" * 40
    artifact_sha = tree_sha256(root)
    deployment_id = "dpl_new"
    transport = _FakeVercelTransport(
        [
            (201, {"id": deployment_id, "readyState": "QUEUED"}),
            (
                200,
                _ready(
                    deployment_id=deployment_id,
                    source_sha=source_sha,
                    artifact_sha=artifact_sha,
                ),
            ),
            (202, {}),
            (200, {"aliases": [{"alias": "preview-branch.vercel.app"}]}),
            (200, {"aliases": [{"alias": "customer-site.vercel.app"}]}),
        ],
        probe_results=[
            (200, "https://generated-preview.vercel.app/"),
            (200, "https://customer-site.vercel.app/"),
        ],
    )

    receipt = _adapter(transport).deploy(
        root,
        source_commit_sha=source_sha,
        expected_artifact_sha256=artifact_sha,
        rollback_reference="dpl_previous",
        authorization_proven=True,
        budget_proven=True,
        now=datetime(2026, 8, 17, 0, 0, tzinfo=timezone.utc),
    )

    assert receipt.contract == "web.deployment-receipt.v1"
    assert receipt.provider == "vercel.web-deployment.v1"
    assert receipt.deployment_id == deployment_id
    assert receipt.source_commit_sha == source_sha
    assert receipt.artifact_sha256 == artifact_sha
    assert receipt.live_url == "https://customer-site.vercel.app"
    assert receipt.health == "HEALTHY_PUBLIC_PRODUCTION"
    assert receipt.rollback_reference == "dpl_previous"
    assert receipt.public_production_proven is True

    create = transport.calls[0]
    assert create[0:2] == ("POST", "/v13/deployments")
    body = create[2]
    assert body is not None
    assert "target" not in body
    metadata = body["meta"]
    assert isinstance(metadata, dict)
    assert metadata["ilaiosSourceCommitSha"] == source_sha
    assert metadata["ilaiosArtifactSha256"] == artifact_sha
    files = body["files"]
    assert isinstance(files, list)
    assert {item["file"] for item in files if isinstance(item, dict)} == {
        "app/page.tsx",
        "package.json",
    }
    assert transport.calls[2][0:2] == (
        "POST",
        f"/v10/projects/prj_test/promote/{deployment_id}",
    )
    assert transport.calls[3][0:2] == (
        "GET",
        f"/v2/deployments/{deployment_id}/aliases",
    )
    assert transport.calls[4][0:2] == (
        "GET",
        f"/v2/deployments/{deployment_id}/aliases",
    )
    assert transport.probes == [
        "https://generated-preview.vercel.app",
        "https://customer-site.vercel.app",
    ]


def _assert_governance_rejection_before_credential(
    tmp_path: Path,
    *,
    authorization_proven: bool,
    budget_proven: bool,
    message: str,
) -> None:
    root = _project(tmp_path)
    credential_reads = 0
    transport = _FakeVercelTransport([])

    def credential() -> str:
        nonlocal credential_reads
        credential_reads += 1
        return "vercel-test-token"

    adapter = VercelWebDeploymentAdapter(
        team_id="team_test",
        project_id="prj_test",
        project_name="ilaios-generated-test",
        production_alias="customer-site.vercel.app",
        credential_provider=credential,
        transport=transport,
    )

    with pytest.raises(WebDeploymentError, match=message):
        adapter.deploy(
            root,
            source_commit_sha="a" * 40,
            authorization_proven=authorization_proven,
            budget_proven=budget_proven,
        )

    assert credential_reads == 0
    assert transport.calls == []


def test_vercel_deploy_requires_authorization_before_credential_or_network(
    tmp_path: Path,
) -> None:
    _assert_governance_rejection_before_credential(
        tmp_path,
        authorization_proven=False,
        budget_proven=True,
        message="authorization is not proven",
    )


def test_vercel_deploy_requires_budget_before_credential_or_network(
    tmp_path: Path,
) -> None:
    _assert_governance_rejection_before_credential(
        tmp_path,
        authorization_proven=True,
        budget_proven=False,
        message="budget is not proven",
    )


def test_vercel_deploy_fails_closed_on_provider_provenance_mismatch(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path)
    source_sha = "a" * 40
    artifact_sha = tree_sha256(root)
    deployment_id = "dpl_bad_provenance"
    ready = _ready(
        deployment_id=deployment_id,
        source_sha=source_sha,
        artifact_sha=artifact_sha,
    )
    metadata = ready["meta"]
    assert isinstance(metadata, dict)
    metadata["ilaiosArtifactSha256"] = "f" * 64
    transport = _FakeVercelTransport(
        [
            (201, {"id": deployment_id}),
            (200, ready),
        ]
    )

    with pytest.raises(WebDeploymentError, match="artifact provenance mismatch"):
        _adapter(transport).deploy(
            root,
            source_commit_sha=source_sha,
            expected_artifact_sha256=artifact_sha,
            authorization_proven=True,
            budget_proven=True,
        )

    assert len(transport.calls) == 2
    assert all("promote" not in call[1] for call in transport.calls)
    assert transport.probes == []


def test_vercel_deploy_rejects_environment_secret_files_before_credential(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path)
    (root / ".env.production").write_text("SECRET=value\n", encoding="utf-8")
    credential_reads = 0

    def credential() -> str:
        nonlocal credential_reads
        credential_reads += 1
        return "vercel-test-token"

    transport = _FakeVercelTransport([])
    adapter = VercelWebDeploymentAdapter(
        team_id="team_test",
        project_id="prj_test",
        project_name="ilaios-generated-test",
        production_alias="customer-site.vercel.app",
        credential_provider=credential,
        transport=transport,
    )

    with pytest.raises(WebDeploymentError, match="environment secret file"):
        adapter.deploy(
            root,
            source_commit_sha="a" * 40,
            authorization_proven=True,
            budget_proven=True,
        )

    assert credential_reads == 0
    assert transport.calls == []


def test_vercel_deploy_rejects_inline_source_over_budget_before_credential(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path)
    credential_reads = 0

    def credential() -> str:
        nonlocal credential_reads
        credential_reads += 1
        return "vercel-test-token"

    transport = _FakeVercelTransport([])
    adapter = VercelWebDeploymentAdapter(
        team_id="team_test",
        project_id="prj_test",
        project_name="ilaios-generated-test",
        production_alias="customer-site.vercel.app",
        credential_provider=credential,
        transport=transport,
        max_inline_bytes=8,
    )

    with pytest.raises(WebDeploymentError, match="bounded upload budget"):
        adapter.deploy(
            root,
            source_commit_sha="a" * 40,
            authorization_proven=True,
            budget_proven=True,
        )

    assert credential_reads == 0
    assert transport.calls == []


def test_vercel_deploy_does_not_promote_when_preview_health_fails(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path)
    source_sha = "b" * 40
    artifact_sha = tree_sha256(root)
    deployment_id = "dpl_unhealthy"
    transport = _FakeVercelTransport(
        [
            (201, {"id": deployment_id}),
            (
                200,
                _ready(
                    deployment_id=deployment_id,
                    source_sha=source_sha,
                    artifact_sha=artifact_sha,
                ),
            ),
        ],
        probe_results=[(503, "https://generated-preview.vercel.app/")],
    )

    with pytest.raises(WebDeploymentError, match="health probe failed"):
        _adapter(transport).deploy(
            root,
            source_commit_sha=source_sha,
            expected_artifact_sha256=artifact_sha,
            authorization_proven=True,
            budget_proven=True,
        )

    assert [call[1] for call in transport.calls] == [
        "/v13/deployments",
        f"/v13/deployments/{deployment_id}",
    ]


def test_vercel_deploy_rejects_preview_health_redirect_to_other_host(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path)
    source_sha = "b" * 40
    artifact_sha = tree_sha256(root)
    deployment_id = "dpl_redirected"
    transport = _FakeVercelTransport(
        [
            (201, {"id": deployment_id}),
            (
                200,
                _ready(
                    deployment_id=deployment_id,
                    source_sha=source_sha,
                    artifact_sha=artifact_sha,
                ),
            ),
        ],
        probe_results=[(200, "https://attacker.example/")],
    )

    with pytest.raises(WebDeploymentError, match="unexpected host"):
        _adapter(transport).deploy(
            root,
            source_commit_sha=source_sha,
            expected_artifact_sha256=artifact_sha,
            authorization_proven=True,
            budget_proven=True,
        )

    assert all("promote" not in call[1] for call in transport.calls)


def test_vercel_deploy_never_accepts_unexpected_alias_as_production(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path)
    source_sha = "e" * 40
    artifact_sha = tree_sha256(root)
    deployment_id = "dpl_wrong_alias"
    transport = _FakeVercelTransport(
        [
            (201, {"id": deployment_id}),
            (
                200,
                _ready(
                    deployment_id=deployment_id,
                    source_sha=source_sha,
                    artifact_sha=artifact_sha,
                ),
            ),
            (201, {}),
            (200, {"aliases": [{"alias": "preview-one.vercel.app"}]}),
            (200, {"aliases": [{"alias": "preview-two.vercel.app"}]}),
            (200, {"aliases": [{"alias": "preview-three.vercel.app"}]}),
        ],
        probe_results=[(200, "https://generated-preview.vercel.app/")],
    )

    with pytest.raises(WebDeploymentError, match="expected Vercel production alias"):
        _adapter(transport).deploy(
            root,
            source_commit_sha=source_sha,
            expected_artifact_sha256=artifact_sha,
            authorization_proven=True,
            budget_proven=True,
        )

    assert transport.probes == ["https://generated-preview.vercel.app"]


def test_vercel_rollback_reconciles_provenance_expected_alias_and_health() -> None:
    source_sha = "c" * 40
    artifact_sha = "d" * 64
    deployment_id = "dpl_previous"
    transport = _FakeVercelTransport(
        [
            (201, {}),
            (
                200,
                _ready(
                    deployment_id=deployment_id,
                    source_sha=source_sha,
                    artifact_sha=artifact_sha,
                ),
            ),
            (200, {"aliases": [{"alias": "restored.vercel.app"}]}),
        ],
        probe_results=[
            (200, "https://generated-preview.vercel.app/"),
            (200, "https://restored.vercel.app/"),
        ],
    )

    receipt = _adapter(
        transport,
        production_alias="restored.vercel.app",
    ).rollback(
        deployment_id,
        source_commit_sha=source_sha,
        expected_artifact_sha256=artifact_sha,
        replaced_deployment_id="dpl_broken",
        authorization_proven=True,
        budget_proven=True,
        now=datetime(2026, 8, 17, 0, 1, tzinfo=timezone.utc),
    )

    assert receipt.deployment_id == deployment_id
    assert receipt.health == "HEALTHY_PUBLIC_ROLLBACK"
    assert receipt.rollback_reference == "dpl_broken"
    assert receipt.live_url == "https://restored.vercel.app"
    assert receipt.public_production_proven is True
    assert transport.calls[0] == (
        "POST",
        f"/v1/projects/prj_test/rollback/{deployment_id}",
        None,
    )
    assert transport.probes == [
        "https://generated-preview.vercel.app",
        "https://restored.vercel.app",
    ]


def test_vercel_rollback_rejects_undocumented_success_code() -> None:
    transport = _FakeVercelTransport([(202, {})])

    with pytest.raises(WebDeploymentError, match="rollback request failed"):
        _adapter(transport).rollback(
            "dpl_previous",
            source_commit_sha="c" * 40,
            expected_artifact_sha256="d" * 64,
            authorization_proven=True,
            budget_proven=True,
        )


def test_production_alias_must_be_a_bare_https_host() -> None:
    transport = _FakeVercelTransport([])

    with pytest.raises(ValueError, match="hostname, not a path URL"):
        VercelWebDeploymentAdapter(
            team_id="team_test",
            project_id="prj_test",
            project_name="ilaios-generated-test",
            production_alias="https://customer-site.vercel.app/path",
            credential_provider=lambda: "vercel-test-token",
            transport=transport,
        )

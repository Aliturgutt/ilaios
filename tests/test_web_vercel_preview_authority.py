"""Adversarial coverage for Web preview/deploy authority separation."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

import pytest

from services.integrations.web_delivery import WebDeploymentError, tree_sha256
from services.integrations.web_vercel_delivery import VercelWebDeploymentAdapter


class _Transport:
    def __init__(
        self,
        responses: list[tuple[int, Mapping[str, object]]],
        *,
        probes: list[tuple[int, str]] | None = None,
    ) -> None:
        self.responses = deque(responses)
        self.probe_results = deque(probes or [])
        self.calls: list[tuple[str, str, Mapping[str, object] | None]] = []
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
        assert token == "test-token"
        assert team_id == "team_test"
        self.calls.append((method, path, json_body))
        if not self.responses:
            raise AssertionError("unexpected provider API call")
        return self.responses.popleft()

    def probe(self, url: str) -> tuple[int, str]:
        self.probes.append(url)
        if not self.probe_results:
            raise AssertionError("unexpected provider health probe")
        return self.probe_results.popleft()


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "app").mkdir(parents=True)
    (root / "package.json").write_text(
        '{"scripts":{"build":"next build"},"dependencies":{"next":"16.2.11"}}\n',
        encoding="utf-8",
    )
    (root / "app/page.tsx").write_text(
        "export default function Page(){return <main>preview</main>}\n",
        encoding="utf-8",
    )
    return root


def _ready(
    *,
    deployment_id: str,
    source_sha: str,
    artifact_sha: str,
    host: str = "generated-preview.vercel.app",
) -> dict[str, object]:
    return {
        "id": deployment_id,
        "readyState": "READY",
        "url": host,
        "meta": {
            "ilaiosSourceCommitSha": source_sha,
            "ilaiosArtifactSha256": artifact_sha,
            "ilaiosDeploymentContract": "web.deployment-receipt.v1",
        },
    }


def _adapter(transport: _Transport) -> VercelWebDeploymentAdapter:
    return VercelWebDeploymentAdapter(
        team_id="team_test",
        project_id="prj_test",
        project_name="generated-test",
        production_alias="customer-site.vercel.app",
        credential_provider=lambda: "test-token",
        transport=transport,
        max_poll_attempts=2,
        poll_interval_seconds=0,
        sleeper=lambda _seconds: None,
    )


def test_preview_is_terminal_and_never_promotes_or_reads_production_alias(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path)
    source_sha = "a" * 40
    artifact_sha = tree_sha256(root)
    deployment_id = "dpl_preview"
    transport = _Transport(
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
        probes=[(200, "https://generated-preview.vercel.app/")],
    )

    receipt = _adapter(transport).preview(
        root,
        source_commit_sha=source_sha,
        expected_artifact_sha256=artifact_sha,
        preview_authorization_proven=True,
        budget_proven=True,
        now=datetime(2026, 8, 28, 0, 0, tzinfo=timezone.utc),
    )

    assert receipt.live_url == "https://generated-preview.vercel.app"
    assert receipt.health == "HEALTHY_PUBLIC_PREVIEW"
    assert receipt.public_production_proven is False
    assert receipt.rollback_reference is None
    assert all("promote" not in path for _, path, _ in transport.calls)
    assert all("aliases" not in path for _, path, _ in transport.calls)
    body = transport.calls[0][2]
    assert body is not None
    assert "target" not in body
    settings = body["projectSettings"]
    assert isinstance(settings, dict)
    assert settings["installCommand"] == "npm install --ignore-scripts"


def test_preview_requires_its_own_authorization_before_credentials_or_network(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path)
    credential_reads = 0
    transport = _Transport([])

    def credential() -> str:
        nonlocal credential_reads
        credential_reads += 1
        return "test-token"

    adapter = VercelWebDeploymentAdapter(
        team_id="team_test",
        project_id="prj_test",
        project_name="generated-test",
        production_alias="customer-site.vercel.app",
        credential_provider=credential,
        transport=transport,
    )

    with pytest.raises(WebDeploymentError, match="preview authorization is not proven"):
        adapter.preview(
            root,
            source_commit_sha="a" * 40,
            preview_authorization_proven=False,
            budget_proven=True,
        )

    assert credential_reads == 0
    assert transport.calls == []


def test_preview_fails_closed_when_provider_reuses_production_host(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path)
    source_sha = "b" * 40
    artifact_sha = tree_sha256(root)
    deployment_id = "dpl_bad_preview"
    transport = _Transport(
        [
            (201, {"id": deployment_id}),
            (
                200,
                _ready(
                    deployment_id=deployment_id,
                    source_sha=source_sha,
                    artifact_sha=artifact_sha,
                    host="customer-site.vercel.app",
                ),
            ),
        ]
    )

    with pytest.raises(WebDeploymentError, match="preview host is not isolated"):
        _adapter(transport).preview(
            root,
            source_commit_sha=source_sha,
            expected_artifact_sha256=artifact_sha,
            preview_authorization_proven=True,
            budget_proven=True,
        )

    assert all("promote" not in path for _, path, _ in transport.calls)

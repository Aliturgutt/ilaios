"""Adversarial regression for generated Web deployment package installation."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

import pytest

from services.integrations.web_delivery import WebDeploymentError
from services.integrations.web_vercel_delivery import VercelWebDeploymentAdapter


class _CaptureTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Mapping[str, object] | None]] = []

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
        return 400, {}

    def probe(self, url: str) -> tuple[int, str]:
        raise AssertionError(f"unexpected health probe: {url}")


def test_generated_vercel_install_disables_package_lifecycle_scripts(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    (project / "app").mkdir(parents=True)
    (project / "package.json").write_text(
        '{"scripts":{"preinstall":"node hostile.js","build":"next build"},'
        '"dependencies":{"next":"16.2.11"}}\n',
        encoding="utf-8",
    )
    (project / "app/page.tsx").write_text(
        "export default function Page(){return <main>safe</main>}\n",
        encoding="utf-8",
    )

    transport = _CaptureTransport()
    adapter = VercelWebDeploymentAdapter(
        team_id="team_test",
        project_id="prj_test",
        project_name="generated-test",
        production_alias="customer-site.vercel.app",
        credential_provider=lambda: "test-token",
        transport=transport,
    )

    with pytest.raises(WebDeploymentError, match="deployment creation failed"):
        adapter.deploy(
            project,
            source_commit_sha="a" * 40,
            authorization_proven=True,
            budget_proven=True,
        )

    assert len(transport.calls) == 1
    method, path, body = transport.calls[0]
    assert (method, path) == ("POST", "/v13/deployments")
    assert body is not None
    project_settings = body.get("projectSettings")
    assert isinstance(project_settings, dict)
    assert project_settings.get("installCommand") == "npm install --ignore-scripts"

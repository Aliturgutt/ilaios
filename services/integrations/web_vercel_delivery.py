"""Governed Vercel delivery boundary for certified Web Factory source.

The adapter implements the existing ``web.deployment-receipt.v1`` contract. It is
not a routing, policy, approval, credential, DNS or budget authority. Callers must
prove authorization and budget before any credential or network access.

A new deployment is deliberately created as a preview first. Production is proven
only after READY/provenance reconciliation, immutable-preview HTTPS health,
explicit Vercel promotion, appearance of the predeclared production alias, and
HTTPS health that remains on that expected production host. Rollback is likewise
reconciled against exact source/artifact provenance and the expected live alias.
"""

from __future__ import annotations

import base64
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Mapping, Protocol, cast
from urllib.parse import urlparse

import requests

from .web_delivery import (
    WebDeploymentError,
    WebDeploymentReceipt,
    _timestamp,
    _valid_sha,
    tree_sha256,
)


class VercelDeploymentTransport(Protocol):
    """Small injectable transport so provider behavior is deterministic in tests."""

    def api(
        self,
        method: str,
        path: str,
        *,
        token: str,
        team_id: str,
        json_body: Mapping[str, object] | None = None,
    ) -> tuple[int, Mapping[str, object]]: ...

    def probe(self, url: str) -> tuple[int, str]: ...


class RequestsVercelDeploymentTransport:
    """HTTPS transport for the Vercel REST API and public health probes."""

    def __init__(self, *, timeout_seconds: float = 30.0) -> None:
        if timeout_seconds <= 0:
            raise ValueError("Vercel transport timeout must be positive")
        self.timeout_seconds = timeout_seconds

    def api(
        self,
        method: str,
        path: str,
        *,
        token: str,
        team_id: str,
        json_body: Mapping[str, object] | None = None,
    ) -> tuple[int, Mapping[str, object]]:
        if not path.startswith("/"):
            raise WebDeploymentError("Vercel API path must be absolute")
        response = requests.request(
            method,
            f"https://api.vercel.com{path}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            params={"teamId": team_id},
            json=None if json_body is None else dict(json_body),
            timeout=self.timeout_seconds,
        )
        try:
            value = response.json()
        except ValueError:
            value = {}
        if not isinstance(value, dict):
            value = {"payload": value}
        return response.status_code, cast(dict[str, object], value)

    def probe(self, url: str) -> tuple[int, str]:
        response = requests.get(
            url,
            timeout=self.timeout_seconds,
            allow_redirects=True,
        )
        return response.status_code, response.url


class VercelWebDeploymentAdapter:
    """Fail-closed Vercel preview, promote, health and rollback adapter."""

    provider_id = "vercel.web-deployment.v1"
    deployment_contract = "web.deployment-receipt.v1"

    def __init__(
        self,
        *,
        team_id: str,
        project_id: str,
        project_name: str,
        production_alias: str,
        credential_provider: Callable[[], str],
        transport: VercelDeploymentTransport | None = None,
        max_poll_attempts: int = 30,
        poll_interval_seconds: float = 2.0,
        max_inline_bytes: int = 8 * 1024 * 1024,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if not team_id.strip():
            raise ValueError("Vercel team identifier is required")
        if not project_id.strip() or "/" in project_id:
            raise ValueError("Vercel project identifier is invalid")
        if not project_name.strip():
            raise ValueError("Vercel project name is required")
        if max_poll_attempts < 1:
            raise ValueError("Vercel poll attempt budget must be positive")
        if poll_interval_seconds < 0:
            raise ValueError("Vercel poll interval cannot be negative")
        if max_inline_bytes < 1:
            raise ValueError("Vercel inline byte budget must be positive")
        normalized_alias = _normalize_production_alias(production_alias)
        self.team_id = team_id.strip()
        self.project_id = project_id.strip()
        self.project_name = project_name.strip()
        self.production_alias = normalized_alias
        self.production_host = _hostname(normalized_alias)
        self._credential_provider = credential_provider
        self._transport = transport or RequestsVercelDeploymentTransport()
        self._max_poll_attempts = max_poll_attempts
        self._poll_interval_seconds = poll_interval_seconds
        self._max_inline_bytes = max_inline_bytes
        self._sleeper = sleeper

    def preview(
        self,
        project_root: Path,
        *,
        source_commit_sha: str,
        expected_artifact_sha256: str | None = None,
        preview_authorization_proven: bool,
        budget_proven: bool,
        now: datetime | None = None,
    ) -> WebDeploymentReceipt:
        """Create and verify an immutable preview without production authority.

        Preview is deliberately a terminal operation: it never calls the Vercel
        promotion or production-alias endpoints, and its receipt can never be
        mistaken for public-production evidence.
        """

        self._assert_preview_side_effect_authorized(
            preview_authorization_proven=preview_authorization_proven,
            budget_proven=budget_proven,
        )
        deployment_id, artifact_sha, preview_url = self._create_healthy_preview(
            project_root,
            source_commit_sha=source_commit_sha,
            expected_artifact_sha256=expected_artifact_sha256,
        )
        return WebDeploymentReceipt(
            contract=self.deployment_contract,
            provider=self.provider_id,
            deployment_id=deployment_id,
            source_commit_sha=source_commit_sha,
            artifact_sha256=artifact_sha,
            live_url=preview_url,
            health="HEALTHY_PUBLIC_PREVIEW",
            rollback_reference=None,
            deployed_at=_timestamp(now),
            public_production_proven=False,
        )

    def deploy(
        self,
        project_root: Path,
        *,
        source_commit_sha: str,
        expected_artifact_sha256: str | None = None,
        rollback_reference: str | None = None,
        authorization_proven: bool,
        budget_proven: bool,
        now: datetime | None = None,
    ) -> WebDeploymentReceipt:
        self._assert_public_side_effect_authorized(
            authorization_proven=authorization_proven,
            budget_proven=budget_proven,
        )
        deployment_id, artifact_sha, _preview_url = self._create_healthy_preview(
            project_root,
            source_commit_sha=source_commit_sha,
            expected_artifact_sha256=expected_artifact_sha256,
        )
        token = self._credential()
        self._promote(deployment_id, token=token)
        live_url = self._await_expected_production_alias(deployment_id, token=token)
        self._assert_healthy_https(live_url, expected_host=self.production_host)
        return WebDeploymentReceipt(
            contract=self.deployment_contract,
            provider=self.provider_id,
            deployment_id=deployment_id,
            source_commit_sha=source_commit_sha,
            artifact_sha256=artifact_sha,
            live_url=live_url,
            health="HEALTHY_PUBLIC_PRODUCTION",
            rollback_reference=rollback_reference,
            deployed_at=_timestamp(now),
            public_production_proven=True,
        )

    def rollback(
        self,
        deployment_id: str,
        *,
        source_commit_sha: str,
        expected_artifact_sha256: str,
        replaced_deployment_id: str | None = None,
        authorization_proven: bool,
        budget_proven: bool,
        now: datetime | None = None,
    ) -> WebDeploymentReceipt:
        self._assert_public_side_effect_authorized(
            authorization_proven=authorization_proven,
            budget_proven=budget_proven,
        )
        if not deployment_id.startswith("dpl_"):
            raise WebDeploymentError("Vercel rollback deployment id is malformed")
        if not _valid_sha(source_commit_sha):
            raise WebDeploymentError("Vercel rollback source commit SHA is malformed")
        if len(expected_artifact_sha256) != 64 or any(
            character not in "0123456789abcdef"
            for character in expected_artifact_sha256
        ):
            raise WebDeploymentError("Vercel rollback artifact digest is malformed")
        token = self._credential()
        status, _ = self._transport.api(
            "POST",
            f"/v1/projects/{self.project_id}/rollback/{deployment_id}",
            token=token,
            team_id=self.team_id,
        )
        # Current Vercel REST contract documents 201 for a successful rollback.
        if status != 201:
            raise WebDeploymentError(
                f"Vercel rollback request failed with HTTP {status}"
            )
        ready = self._await_ready(deployment_id, token=token)
        self._assert_provider_provenance(
            ready,
            source_commit_sha=source_commit_sha,
            artifact_sha256=expected_artifact_sha256,
        )
        preview_url = self._deployment_url(ready)
        self._assert_preview_host_isolated(preview_url)
        self._assert_healthy_https(preview_url, expected_host=_hostname(preview_url))
        live_url = self._await_expected_production_alias(deployment_id, token=token)
        self._assert_healthy_https(live_url, expected_host=self.production_host)
        return WebDeploymentReceipt(
            contract=self.deployment_contract,
            provider=self.provider_id,
            deployment_id=deployment_id,
            source_commit_sha=source_commit_sha,
            artifact_sha256=expected_artifact_sha256,
            live_url=live_url,
            health="HEALTHY_PUBLIC_ROLLBACK",
            rollback_reference=replaced_deployment_id,
            deployed_at=_timestamp(now),
            public_production_proven=True,
        )

    def _create_healthy_preview(
        self,
        project_root: Path,
        *,
        source_commit_sha: str,
        expected_artifact_sha256: str | None,
    ) -> tuple[str, str, str]:
        source = project_root.resolve()
        if not source.is_dir():
            raise WebDeploymentError("Vercel Web deployment source project is missing")
        if not _valid_sha(source_commit_sha):
            raise WebDeploymentError("Vercel Web source commit SHA is malformed")
        artifact_sha = tree_sha256(source)
        if expected_artifact_sha256 and artifact_sha != expected_artifact_sha256:
            raise WebDeploymentError("Vercel Web deployment artifact digest mismatch")
        files = self._inline_project_files(source)
        token = self._credential()

        # Deliberately omit target=production. The deployment remains preview-only
        # unless the explicit production path subsequently calls _promote().
        create_body: dict[str, object] = {
            "name": self.project_name,
            "project": self.project_id,
            "files": files,
            "gitMetadata": {
                "commitRef": "ilaios-generated",
                "commitSha": source_commit_sha,
                "dirty": False,
                "ci": True,
                "ciType": "ilaios",
            },
            "meta": self._provenance(source_commit_sha, artifact_sha),
            "projectSettings": {
                "framework": "nextjs",
                "buildCommand": "npm run build",
                "installCommand": "npm install --ignore-scripts",
            },
        }
        status, created = self._transport.api(
            "POST",
            "/v13/deployments",
            token=token,
            team_id=self.team_id,
            json_body=create_body,
        )
        if status not in {200, 201, 202}:
            raise WebDeploymentError(
                f"Vercel deployment creation failed with HTTP {status}"
            )
        deployment_id = _required_string(created, "id", "Vercel deployment id")
        ready = self._await_ready(deployment_id, token=token)
        self._assert_provider_provenance(
            ready,
            source_commit_sha=source_commit_sha,
            artifact_sha256=artifact_sha,
        )
        preview_url = self._deployment_url(ready)
        self._assert_preview_host_isolated(preview_url)
        self._assert_healthy_https(preview_url, expected_host=_hostname(preview_url))
        return deployment_id, artifact_sha, preview_url

    def _assert_preview_side_effect_authorized(
        self,
        *,
        preview_authorization_proven: bool,
        budget_proven: bool,
    ) -> None:
        if preview_authorization_proven is not True:
            raise WebDeploymentError("Web preview authorization is not proven")
        if budget_proven is not True:
            raise WebDeploymentError("Web preview budget is not proven")

    def _assert_public_side_effect_authorized(
        self,
        *,
        authorization_proven: bool,
        budget_proven: bool,
    ) -> None:
        if authorization_proven is not True:
            raise WebDeploymentError("public Web deployment authorization is not proven")
        if budget_proven is not True:
            raise WebDeploymentError("public Web deployment budget is not proven")

    def _credential(self) -> str:
        token = self._credential_provider().strip()
        if not token:
            raise WebDeploymentError("Vercel credential is unavailable")
        return token

    def _inline_project_files(self, source: Path) -> list[dict[str, object]]:
        ignored_parts = {".git", ".next", "node_modules"}
        files: list[dict[str, object]] = []
        total = 0
        for path in sorted(
            (item for item in source.rglob("*") if item.is_file()),
            key=lambda item: item.relative_to(source).as_posix(),
        ):
            relative = path.relative_to(source)
            if any(part in ignored_parts for part in relative.parts):
                continue
            if path.name == ".env" or (
                path.name.startswith(".env.") and path.name != ".env.example"
            ):
                raise WebDeploymentError(
                    "Vercel Web deployment source contains an environment secret file"
                )
            body = path.read_bytes()
            total += len(body)
            if total > self._max_inline_bytes:
                raise WebDeploymentError(
                    "Vercel inline deployment exceeds bounded upload budget"
                )
            files.append(
                {
                    "file": relative.as_posix(),
                    "data": base64.b64encode(body).decode("ascii"),
                    "encoding": "base64",
                }
            )
        if not files:
            raise WebDeploymentError("Vercel Web deployment contains no source files")
        if not any(item["file"] == "package.json" for item in files):
            raise WebDeploymentError("Vercel Web deployment package.json is missing")
        return files

    def _await_ready(
        self,
        deployment_id: str,
        *,
        token: str,
    ) -> Mapping[str, object]:
        for attempt in range(self._max_poll_attempts):
            status, value = self._transport.api(
                "GET",
                f"/v13/deployments/{deployment_id}",
                token=token,
                team_id=self.team_id,
            )
            if status != 200:
                raise WebDeploymentError(
                    f"Vercel deployment reconciliation failed with HTTP {status}"
                )
            ready_state = str(value.get("readyState", value.get("status", "")))
            if ready_state == "READY":
                if value.get("id") != deployment_id:
                    raise WebDeploymentError("Vercel deployment identity changed")
                return value
            if ready_state in {"ERROR", "CANCELED", "CANCELLED", "BLOCKED"}:
                raise WebDeploymentError(
                    f"Vercel deployment reached terminal state {ready_state}"
                )
            if attempt + 1 < self._max_poll_attempts:
                self._sleeper(self._poll_interval_seconds)
        raise WebDeploymentError("Vercel deployment readiness budget was exhausted")

    def _assert_provider_provenance(
        self,
        deployment: Mapping[str, object],
        *,
        source_commit_sha: str,
        artifact_sha256: str,
    ) -> None:
        metadata = deployment.get("meta")
        if not isinstance(metadata, dict):
            raise WebDeploymentError("Vercel deployment provenance metadata is missing")
        if metadata.get("ilaiosSourceCommitSha") != source_commit_sha:
            raise WebDeploymentError("Vercel deployment source SHA provenance mismatch")
        if metadata.get("ilaiosArtifactSha256") != artifact_sha256:
            raise WebDeploymentError("Vercel deployment artifact provenance mismatch")
        if metadata.get("ilaiosDeploymentContract") != self.deployment_contract:
            raise WebDeploymentError("Vercel deployment contract provenance mismatch")

    def _deployment_url(self, deployment: Mapping[str, object]) -> str:
        value = deployment.get("url")
        if not isinstance(value, str) or not value.strip():
            raise WebDeploymentError("Vercel immutable deployment URL is missing")
        return _https_url(value)

    def _assert_preview_host_isolated(self, preview_url: str) -> None:
        if _hostname(preview_url) == self.production_host:
            raise WebDeploymentError("Vercel preview host is not isolated from production")

    def _promote(self, deployment_id: str, *, token: str) -> None:
        status, _ = self._transport.api(
            "POST",
            f"/v10/projects/{self.project_id}/promote/{deployment_id}",
            token=token,
            team_id=self.team_id,
        )
        # Current Vercel REST contract documents 201/202 for promotion success.
        if status not in {201, 202}:
            raise WebDeploymentError(
                f"Vercel production promotion failed with HTTP {status}"
            )

    def _await_expected_production_alias(
        self,
        deployment_id: str,
        *,
        token: str,
    ) -> str:
        for attempt in range(self._max_poll_attempts):
            status, value = self._transport.api(
                "GET",
                f"/v2/deployments/{deployment_id}/aliases",
                token=token,
                team_id=self.team_id,
            )
            if status != 200:
                raise WebDeploymentError(
                    f"Vercel production alias lookup failed with HTTP {status}"
                )
            aliases = value.get("aliases")
            if not isinstance(aliases, list):
                raise WebDeploymentError("Vercel production alias response is malformed")
            for item in aliases:
                alias: object | None
                if isinstance(item, str):
                    alias = item
                elif isinstance(item, dict):
                    alias = item.get("alias")
                else:
                    alias = None
                if not isinstance(alias, str) or not alias.strip():
                    continue
                candidate = _https_url(alias)
                if _hostname(candidate) == self.production_host:
                    return self.production_alias
            if attempt + 1 < self._max_poll_attempts:
                self._sleeper(self._poll_interval_seconds)
        raise WebDeploymentError("expected Vercel production alias is not proven")

    def _assert_healthy_https(self, live_url: str, *, expected_host: str) -> None:
        if not live_url.startswith("https://"):
            raise WebDeploymentError("Vercel production URL is not HTTPS")
        if _hostname(live_url) != expected_host:
            raise WebDeploymentError("Vercel health target host is unexpected")
        status, final_url = self._transport.probe(live_url)
        if status < 200 or status >= 400:
            raise WebDeploymentError(
                f"Vercel production health probe failed with HTTP {status}"
            )
        if not final_url.startswith("https://"):
            raise WebDeploymentError("Vercel production health redirected away from HTTPS")
        if _hostname(final_url) != expected_host:
            raise WebDeploymentError("Vercel production health redirected to an unexpected host")

    def _provenance(
        self,
        source_commit_sha: str,
        artifact_sha256: str,
    ) -> dict[str, str]:
        return {
            "ilaiosSourceCommitSha": source_commit_sha,
            "ilaiosArtifactSha256": artifact_sha256,
            "ilaiosDeploymentContract": self.deployment_contract,
        }


def _required_string(
    value: Mapping[str, object],
    key: str,
    description: str,
) -> str:
    candidate = value.get(key)
    if not isinstance(candidate, str) or not candidate.strip():
        raise WebDeploymentError(f"{description} is missing")
    return candidate.strip()


def _https_url(value: str) -> str:
    normalized = value.strip().rstrip("/")
    if not normalized:
        raise WebDeploymentError("Vercel URL is empty")
    if normalized.startswith("https://"):
        candidate = normalized
    elif "://" in normalized:
        raise WebDeploymentError("Vercel URL uses a non-HTTPS scheme")
    else:
        candidate = f"https://{normalized}"
    parsed = urlparse(candidate)
    if parsed.scheme != "https" or not parsed.hostname:
        raise WebDeploymentError("Vercel HTTPS URL is malformed")
    if parsed.username is not None or parsed.password is not None:
        raise WebDeploymentError("Vercel URL must not contain credentials")
    return candidate


def _hostname(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise WebDeploymentError("Vercel HTTPS host is malformed")
    return parsed.hostname.casefold()


def _normalize_production_alias(value: str) -> str:
    candidate = _https_url(value)
    parsed = urlparse(candidate)
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError("Vercel production alias must be a hostname, not a path URL")
    if parsed.port not in {None, 443}:
        raise ValueError("Vercel production alias must use the default HTTPS port")
    if parsed.hostname is None:
        raise ValueError("Vercel production alias hostname is required")
    return f"https://{parsed.hostname.casefold()}"


__all__ = [
    "RequestsVercelDeploymentTransport",
    "VercelDeploymentTransport",
    "VercelWebDeploymentAdapter",
]

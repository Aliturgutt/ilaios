"""Bounded read-only external validation for Software Factory breadth evidence.

This module does not add execution authority. It reuses the canonical runtime router,
performs read-only GitHub repository probes, and emits conservative technical
commercial-readiness evidence without claiming legal clearance or production release.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from services.runtime.routing import (
    AgentProfile,
    ProviderProfile,
    SkillArtifact,
    SkillRegistry,
    route_provider,
)

_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_PERMISSIVE_LICENSES = frozenset(
    {
        "MIT",
        "Apache-2.0",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "ISC",
    }
)


class SoftwareFactoryExternalValidationError(RuntimeError):
    """External validation could not be proven safely."""


@dataclass(frozen=True, slots=True)
class ExternalRepositoryEvidence:
    repository: str
    provider: str
    default_branch: str
    head_sha: str
    license_spdx: str
    private: bool
    archived: bool
    read_only: bool


@dataclass(frozen=True, slots=True)
class ProviderRouteEvidence:
    provider_id: str
    capability: str
    deterministic_first: bool
    evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CommercialReadinessEvidence:
    technical_gate_passed: bool
    license_spdx: str
    provider_cost_usd: float
    legal_clearance_claimed: bool
    production_release_claimed: bool
    reasons: tuple[str, ...]


def _github_json(url: str, *, token: str | None, timeout: float = 10.0) -> dict[str, Any]:
    if not url.startswith("https://api.github.com/"):
        raise SoftwareFactoryExternalValidationError("external repository host is not allow-listed")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ilaios-software-factory-external-validation/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise SoftwareFactoryExternalValidationError(
                    f"GitHub read-only probe returned HTTP {response.status}"
                )
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise SoftwareFactoryExternalValidationError("GitHub read-only probe failed") from error
    if not isinstance(payload, dict):
        raise SoftwareFactoryExternalValidationError("GitHub response was not an object")
    return payload


def validate_public_github_repository(
    repository: str,
    *,
    token: str | None = None,
) -> ExternalRepositoryEvidence:
    """Probe one public GitHub repository without mutation and bind exact HEAD evidence."""
    if not _REPOSITORY.fullmatch(repository):
        raise SoftwareFactoryExternalValidationError("repository must be owner/name")
    base = f"https://api.github.com/repos/{repository}"
    metadata = _github_json(base, token=token)
    if metadata.get("private") is not False:
        raise SoftwareFactoryExternalValidationError("only public repositories are allowed")
    default_branch = metadata.get("default_branch")
    if not isinstance(default_branch, str) or not default_branch:
        raise SoftwareFactoryExternalValidationError("repository default branch is missing")
    commit = _github_json(f"{base}/commits/{default_branch}", token=token)
    head_sha = commit.get("sha")
    if not isinstance(head_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", head_sha):
        raise SoftwareFactoryExternalValidationError("repository HEAD SHA is invalid")
    license_payload = _github_json(f"{base}/license", token=token)
    license_obj = license_payload.get("license")
    spdx = license_obj.get("spdx_id") if isinstance(license_obj, dict) else None
    if not isinstance(spdx, str) or not spdx or spdx == "NOASSERTION":
        raise SoftwareFactoryExternalValidationError("repository SPDX license is not proven")
    return ExternalRepositoryEvidence(
        repository=repository,
        provider="github",
        default_branch=default_branch,
        head_sha=head_sha,
        license_spdx=spdx,
        private=False,
        archived=bool(metadata.get("archived", False)),
        read_only=True,
    )


def prove_repository_provider_route() -> ProviderRouteEvidence:
    """Reuse the canonical provider router for the external repository read capability."""
    content = b"software-factory:external-repository-read:v1"
    artifact = SkillArtifact(
        skill_id="ilaios.skill.software.external-repository-read",
        content=content,
        requested_authorities=frozenset({"software.repository.read"}),
        owner="ILAIOS",
        license_id="LicenseRef-ILAIOS-Proprietary",
        source_provenance="ILAIOS-native",
    )
    registry = SkillRegistry()
    registry.approve(
        artifact.skill_id,
        hashlib.sha256(content).hexdigest(),
        frozenset({"software.repository.read"}),
        owner=artifact.owner,
        license_id=artifact.license_id,
        source_provenance=artifact.source_provenance,
    )
    decision = route_provider(
        AgentProfile(
            agent_id="ilaios.agent.software.external-validator",
            authorities=frozenset({"software.repository.read"}),
        ),
        artifact,
        registry,
        (
            ProviderProfile(
                provider_id="github.readonly",
                capabilities=frozenset({"software.repository.read"}),
                deterministic=True,
            ),
        ),
        capability="software.repository.read",
    )
    return ProviderRouteEvidence(
        provider_id=decision.provider_id,
        capability=decision.capability,
        deterministic_first=decision.deterministic_first,
        evidence=decision.evidence,
    )


def assess_commercial_readiness(
    repository: ExternalRepositoryEvidence,
    *,
    provider_cost_usd: float,
) -> CommercialReadinessEvidence:
    """Apply a conservative technical gate; never claim legal or release clearance."""
    if provider_cost_usd < 0:
        raise SoftwareFactoryExternalValidationError("provider cost cannot be negative")
    reasons: list[str] = []
    if repository.license_spdx not in _PERMISSIVE_LICENSES:
        reasons.append("LICENSE_NOT_IN_BOUNDED_PERMISSIVE_SET")
    if repository.archived:
        reasons.append("REPOSITORY_ARCHIVED")
    if provider_cost_usd != 0:
        reasons.append("NONZERO_PROVIDER_COST_REQUIRES_SEPARATE_BUDGET_APPROVAL")
    return CommercialReadinessEvidence(
        technical_gate_passed=not reasons,
        license_spdx=repository.license_spdx,
        provider_cost_usd=provider_cost_usd,
        legal_clearance_claimed=False,
        production_release_claimed=False,
        reasons=tuple(reasons),
    )


def validate_external_scope(repository: str, *, token: str | None = None) -> dict[str, object]:
    repo = validate_public_github_repository(repository, token=token)
    route = prove_repository_provider_route()
    commercial = assess_commercial_readiness(repo, provider_cost_usd=0.0)
    if not commercial.technical_gate_passed:
        raise SoftwareFactoryExternalValidationError("technical commercial-readiness gate failed")
    return {
        "scope": "SOFTWARE_FACTORY_EXTERNAL_VALIDATION",
        "repository": asdict(repo),
        "provider_route": asdict(route),
        "commercial_readiness": asdict(commercial),
        "mutation_performed": False,
        "external_effect_authority_added": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = validate_external_scope(args.repository, token=os.getenv("GITHUB_TOKEN"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

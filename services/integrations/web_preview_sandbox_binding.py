"""Bind trusted Web preview sandbox observations to exact deployment receipts.

This module is an evidence binding layer only. It does not create a preview runtime,
perform deployment, own credentials, or grant publish authority. It prevents a
trusted sandbox observation or isolation attestation from being reused across
another preview URL or artifact lineage. Source/execution/tenant binding remains
enforced by the incumbent sandbox observer/evidence contracts.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from services.integrations.web_delivery import WebDeploymentError, WebDeploymentReceipt
from services.software_factory import ExecutionPolicy
from services.web_app_preview_runtime_probe import (
    PreviewHttpTransport,
    PreviewIsolationBoundaryFacts,
    probe_preview_runtime_boundary,
)
from services.web_app_preview_sandbox_observer import (
    PreviewRuntimeBoundaryObservation,
    observe_generated_preview_sandbox,
)
from services.web_app_sandbox_evidence import GeneratedPreviewSandboxObservation

_COMMIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ISOLATION_ATTESTATION_CONTRACT = "web.preview-isolation-attestation.v1"


@dataclass(frozen=True, slots=True)
class PreviewIsolationAttestation:
    """Trusted runtime-boundary facts bound to one immutable preview deployment.

    The attestation deliberately carries no authority. Its purpose is to prevent
    otherwise-valid isolation facts from being replayed across another deployment,
    source commit, artifact, provider, or preview origin before the HTTP observation
    is produced.
    """

    contract: str
    provider: str
    deployment_id: str
    source_commit_sha: str
    artifact_sha256: str
    preview_origin: str
    facts: PreviewIsolationBoundaryFacts


def probe_and_bind_preview_sandbox_to_receipt(
    *,
    receipt: WebDeploymentReceipt,
    execution_id: str,
    tenant_id: str,
    source_sha256: str,
    privileged_session_origin: str,
    isolation_attestation: PreviewIsolationAttestation,
    policy: ExecutionPolicy,
    transport: PreviewHttpTransport | None = None,
    timeout_seconds: int = 15,
) -> GeneratedPreviewSandboxObservation:
    """Probe the exact receipt URL using exact-lineage runtime isolation facts."""
    _validate_preview_receipt(receipt)
    isolation = bind_isolation_attestation_to_receipt(
        receipt=receipt,
        attestation=isolation_attestation,
    )
    runtime = probe_preview_runtime_boundary(
        preview_url=receipt.live_url,
        execution_id=execution_id,
        tenant_id=tenant_id,
        source_sha256=source_sha256,
        artifact_sha256=receipt.artifact_sha256,
        privileged_session_origin=privileged_session_origin,
        isolation=isolation,
        transport=transport,
        timeout_seconds=timeout_seconds,
    )
    return bind_preview_sandbox_to_receipt(receipt=receipt, runtime=runtime, policy=policy)


def bind_isolation_attestation_to_receipt(
    *,
    receipt: WebDeploymentReceipt,
    attestation: PreviewIsolationAttestation,
) -> PreviewIsolationBoundaryFacts:
    """Accept trusted isolation facts only for the exact canonical preview receipt."""
    _validate_preview_receipt(receipt)
    if attestation.contract != _ISOLATION_ATTESTATION_CONTRACT:
        raise WebDeploymentError("preview isolation attestation contract is not canonical")
    if attestation.provider != receipt.provider:
        raise WebDeploymentError("preview isolation provider does not match deployment receipt")
    if attestation.deployment_id != receipt.deployment_id:
        raise WebDeploymentError("preview isolation deployment does not match deployment receipt")
    if _COMMIT_SHA_RE.fullmatch(attestation.source_commit_sha) is None:
        raise WebDeploymentError("preview isolation source commit SHA is malformed")
    if attestation.source_commit_sha != receipt.source_commit_sha:
        raise WebDeploymentError("preview isolation source commit does not match deployment receipt")
    artifact_sha = attestation.artifact_sha256.casefold()
    if _SHA256_RE.fullmatch(artifact_sha) is None:
        raise WebDeploymentError("preview isolation artifact digest is malformed")
    if artifact_sha != receipt.artifact_sha256.casefold():
        raise WebDeploymentError("preview isolation artifact does not match deployment receipt")
    if _origin(attestation.preview_origin) != _origin(receipt.live_url):
        raise WebDeploymentError("preview isolation origin does not match deployment receipt")
    return attestation.facts


def bind_preview_sandbox_to_receipt(
    *,
    receipt: WebDeploymentReceipt,
    runtime: PreviewRuntimeBoundaryObservation,
    policy: ExecutionPolicy,
) -> GeneratedPreviewSandboxObservation:
    """Return sandbox evidence only when runtime and preview receipt are exact-lineage bound."""
    _validate_preview_receipt(receipt)
    if runtime.artifact_sha256.lower() != receipt.artifact_sha256.lower():
        raise WebDeploymentError("preview runtime artifact does not match deployment receipt")
    receipt_origin = _origin(receipt.live_url)
    if _origin(runtime.http.final_url) != receipt_origin:
        raise WebDeploymentError("preview runtime URL does not match deployment receipt")

    observation = observe_generated_preview_sandbox(runtime=runtime, policy=policy)
    if observation.generated_runtime_origin != receipt_origin:
        raise WebDeploymentError("preview observation origin does not match deployment receipt")
    return observation


def _validate_preview_receipt(receipt: WebDeploymentReceipt) -> None:
    if receipt.contract != "web.deployment-receipt.v1":
        raise WebDeploymentError("preview receipt contract is not canonical")
    if receipt.public_production_proven:
        raise WebDeploymentError("production receipt cannot be used as preview sandbox evidence")
    if not receipt.deployment_id.strip() or not receipt.provider.strip():
        raise WebDeploymentError("preview receipt identity is incomplete")
    if _COMMIT_SHA_RE.fullmatch(receipt.source_commit_sha) is None:
        raise WebDeploymentError("preview receipt source commit SHA is malformed")
    artifact_sha = receipt.artifact_sha256.casefold()
    if _SHA256_RE.fullmatch(artifact_sha) is None:
        raise WebDeploymentError("preview receipt artifact digest is malformed")
    if receipt.health not in {"HEALTHY_PUBLIC_PREVIEW", "HEALTHY_SANDBOX_PREVIEW"}:
        raise WebDeploymentError("preview receipt health is not accepted for sandbox evidence")


def _origin(value: str) -> str:
    try:
        parsed = urlsplit(value.strip())
        port = parsed.port
    except ValueError as error:
        raise WebDeploymentError("preview receipt URL is malformed") from error
    if parsed.scheme.casefold() != "https" or parsed.hostname is None:
        raise WebDeploymentError("preview receipt URL must be HTTPS")
    if parsed.username is not None or parsed.password is not None:
        raise WebDeploymentError("preview receipt URL cannot contain userinfo")
    host = parsed.hostname.casefold().rstrip(".")
    if not host:
        raise WebDeploymentError("preview receipt host is invalid")
    return f"https://{host}" if port in (None, 443) else f"https://{host}:{port}"


__all__ = [
    "PreviewIsolationAttestation",
    "bind_isolation_attestation_to_receipt",
    "bind_preview_sandbox_to_receipt",
    "probe_and_bind_preview_sandbox_to_receipt",
]

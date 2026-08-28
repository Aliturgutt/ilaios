"""Bind trusted Web preview sandbox observations to exact deployment receipts.

This module is an evidence binding layer only. It does not create a preview runtime,
perform deployment, own credentials, or grant publish authority. It prevents a
trusted sandbox observation from being reused across another preview URL or
artifact lineage. Source/execution/tenant binding remains enforced by the incumbent
sandbox observer/evidence contracts.
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit

from services.integrations.web_delivery import WebDeploymentError, WebDeploymentReceipt
from services.software_factory import ExecutionPolicy
from services.web_app_preview_sandbox_observer import (
    PreviewRuntimeBoundaryObservation,
    observe_generated_preview_sandbox,
)
from services.web_app_sandbox_evidence import GeneratedPreviewSandboxObservation

_COMMIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def bind_preview_sandbox_to_receipt(
    *,
    receipt: WebDeploymentReceipt,
    runtime: PreviewRuntimeBoundaryObservation,
    policy: ExecutionPolicy,
) -> GeneratedPreviewSandboxObservation:
    """Return sandbox evidence only when runtime and preview receipt are exact-lineage bound."""
    if receipt.contract != "web.deployment-receipt.v1":
        raise WebDeploymentError("preview receipt contract is not canonical")
    if receipt.public_production_proven:
        raise WebDeploymentError("production receipt cannot be used as preview sandbox evidence")
    if not receipt.deployment_id.strip() or not receipt.provider.strip():
        raise WebDeploymentError("preview receipt identity is incomplete")
    if _COMMIT_SHA_RE.fullmatch(receipt.source_commit_sha) is None:
        raise WebDeploymentError("preview receipt source commit SHA is malformed")
    if receipt.health not in {"HEALTHY_PUBLIC_PREVIEW", "HEALTHY_SANDBOX_PREVIEW"}:
        raise WebDeploymentError("preview receipt health is not accepted for sandbox evidence")
    if runtime.artifact_sha256.lower() != receipt.artifact_sha256.lower():
        raise WebDeploymentError("preview runtime artifact does not match deployment receipt")
    receipt_origin = _origin(receipt.live_url)
    if _origin(runtime.http.final_url) != receipt_origin:
        raise WebDeploymentError("preview runtime URL does not match deployment receipt")

    observation = observe_generated_preview_sandbox(runtime=runtime, policy=policy)
    if observation.generated_runtime_origin != receipt_origin:
        raise WebDeploymentError("preview observation origin does not match deployment receipt")
    return observation


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

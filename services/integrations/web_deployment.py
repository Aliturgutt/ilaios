"""Provider-neutral deployment receipt contract for finished Web Factory artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from urllib.parse import urlparse

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class WebDeploymentReceiptError(ValueError):
    """Raised when external deployment evidence cannot prove exact artifact lineage."""


@dataclass(frozen=True, slots=True)
class WebDeploymentReceipt:
    contract_version: str
    provider: str
    deployment_id: str
    site_id: str
    source_commit_sha: str
    artifact_digest: str
    live_url: str
    rollback_reference: str
    health_verified: bool
    browser_verified: bool
    deployed_at: str

    def evidence_hash(self) -> str:
        payload = json.dumps(
            asdict(self), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


def validate_web_deployment_receipt(
    receipt: WebDeploymentReceipt,
    *,
    expected_site_id: str,
    expected_source_commit_sha: str,
    expected_artifact_digest: str,
) -> str:
    """Validate an external deployment result without granting deployment authority.

    The Web Factory may consume this evidence only after a canonical deployment
    actuator has already produced it. This function never performs network,
    provider, DNS, secret, billing, or deployment mutations.
    """
    if receipt.contract_version != "1.0":
        raise WebDeploymentReceiptError("unsupported web deployment receipt version")
    for field_name in (
        "provider",
        "deployment_id",
        "site_id",
        "live_url",
        "rollback_reference",
        "deployed_at",
    ):
        value = getattr(receipt, field_name)
        if not value or value != value.strip():
            raise WebDeploymentReceiptError(f"invalid deployment receipt {field_name}")
    if not _HEX40.fullmatch(receipt.source_commit_sha):
        raise WebDeploymentReceiptError("deployment receipt source SHA is invalid")
    if not _HEX64.fullmatch(receipt.artifact_digest):
        raise WebDeploymentReceiptError("deployment receipt artifact digest is invalid")
    if receipt.site_id != expected_site_id:
        raise WebDeploymentReceiptError("deployment receipt site identity mismatch")
    if receipt.source_commit_sha != expected_source_commit_sha:
        raise WebDeploymentReceiptError("deployment receipt source SHA mismatch")
    if receipt.artifact_digest != expected_artifact_digest:
        raise WebDeploymentReceiptError("deployment receipt artifact digest mismatch")
    if not receipt.health_verified:
        raise WebDeploymentReceiptError("deployment health verification is required")
    if not receipt.browser_verified:
        raise WebDeploymentReceiptError("deployment browser verification is required")

    parsed = urlparse(receipt.live_url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise WebDeploymentReceiptError("deployment live URL must be a clean HTTPS URL")
    if parsed.hostname.casefold() in {"localhost", "127.0.0.1", "::1"}:
        raise WebDeploymentReceiptError("production deployment receipt cannot target loopback")
    return receipt.evidence_hash()

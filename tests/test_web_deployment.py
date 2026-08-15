"""Fail-closed provider-neutral Web Factory deployment evidence tests."""

from __future__ import annotations

from dataclasses import replace

import pytest

from services.integrations.web_deployment import (
    WebDeploymentReceipt,
    WebDeploymentReceiptError,
    validate_web_deployment_receipt,
)

_SOURCE_SHA = "a" * 40
_ARTIFACT_SHA = "b" * 64


def _receipt() -> WebDeploymentReceipt:
    return WebDeploymentReceipt(
        contract_version="1.0",
        provider="example-static-host",
        deployment_id="deployment-123",
        site_id="site-1234567890abcdefabcd",
        source_commit_sha=_SOURCE_SHA,
        artifact_digest=_ARTIFACT_SHA,
        live_url="https://site.example.test/",
        rollback_reference="deployment-122",
        health_verified=True,
        browser_verified=True,
        deployed_at="2026-08-16T00:00:00+00:00",
    )


def _validate(receipt: WebDeploymentReceipt) -> str:
    return validate_web_deployment_receipt(
        receipt,
        expected_site_id="site-1234567890abcdefabcd",
        expected_source_commit_sha=_SOURCE_SHA,
        expected_artifact_digest=_ARTIFACT_SHA,
    )


def test_exact_deployment_receipt_proves_lineage_and_is_content_addressed() -> None:
    receipt = _receipt()
    first = _validate(receipt)
    second = _validate(receipt)
    assert first == second
    assert len(first) == 64


def test_deployment_receipt_rejects_artifact_or_source_mismatch() -> None:
    with pytest.raises(WebDeploymentReceiptError, match="artifact digest mismatch"):
        _validate(replace(_receipt(), artifact_digest="c" * 64))
    with pytest.raises(WebDeploymentReceiptError, match="source SHA mismatch"):
        _validate(replace(_receipt(), source_commit_sha="d" * 40))


def test_deployment_receipt_requires_health_and_real_browser_verification() -> None:
    with pytest.raises(WebDeploymentReceiptError, match="health verification"):
        _validate(replace(_receipt(), health_verified=False))
    with pytest.raises(WebDeploymentReceiptError, match="browser verification"):
        _validate(replace(_receipt(), browser_verified=False))


def test_deployment_receipt_rejects_unsafe_or_loopback_live_urls() -> None:
    for live_url in (
        "http://site.example.test/",
        "https://user:secret@site.example.test/",
        "https://site.example.test/#fragment",
        "https://localhost/",
        "https://127.0.0.1/",
    ):
        with pytest.raises(WebDeploymentReceiptError):
            _validate(replace(_receipt(), live_url=live_url))

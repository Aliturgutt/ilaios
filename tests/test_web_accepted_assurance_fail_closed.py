"""Regression coverage for accepted Web manifests that predate source assurance."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pytest

from services.integrations.web_product_runtime import WebProductRuntimeError
from services.integrations.web_product_runtime_recovery import RecoverableWebProductRuntime


class _AcceptedConnection:
    def __init__(self, row: dict[str, object]) -> None:
        self._row = row

    def __enter__(self) -> "_AcceptedConnection":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def execute(self, *_args: object, **_kwargs: object) -> "_AcceptedConnection":
        return self

    def fetchone(self) -> dict[str, object]:
        return self._row


class _AcceptedRuntime(RecoverableWebProductRuntime):
    def __init__(self, manifest: dict[str, object]) -> None:
        self._manifest = manifest

    def _connect(self) -> _AcceptedConnection:
        return _AcceptedConnection(
            {
                "status": "accepted",
                "job_id": self._manifest["job_id"],
                "manifest_json": json.dumps(
                    self._manifest, sort_keys=True, separators=(",", ":")
                ),
            }
        )


def _accepted_manifest() -> dict[str, Any]:
    return {
        "adapter_id": "web.product-runtime.v1",
        "request_id": "legacy-accepted-web",
        "job_id": "job-web-1",
        "accepted": True,
        "finalization_status": "accepted",
        "job_state_proven": True,
        "source_assurance": {
            "schema": "ilaios.web.source-assurance.v1",
            "passed": True,
        },
        "qa": {"passed": True, "source_assurance_passed": True},
        "build_result": {
            "status": "SOURCE_CERTIFIED",
            "production_build_required": True,
        },
        "source_project_path": "/tmp/certified-web",
        "source_project_digest": "a" * 64,
        "source_project_files": [{"path": "package.json", "sha256": "b" * 64}],
        "certified_routes": ["/en", "/tr"],
        "design_acceptance": {"status": "PASS"},
        "accessibility_evidence": {"status": "PASS"},
        "seo_evidence": {"status": "PASS"},
        "security_evidence": {"status": "PASS"},
        "performance_evidence": {"status": "PASS"},
    }


def test_assured_accepted_manifest_remains_readable() -> None:
    runtime = _AcceptedRuntime(_accepted_manifest())

    manifest = runtime.get_manifest("legacy-accepted-web")
    assert manifest["accepted"] is True
    recovered = runtime.recover_finalizing(
        "legacy-accepted-web",
        token="unused",
        now=datetime(2026, 8, 17, 0, 0, tzinfo=timezone.utc),
    )
    assert recovered["source_assurance"]["passed"] is True


def test_legacy_accepted_manifest_without_source_assurance_fails_closed() -> None:
    manifest = _accepted_manifest()
    manifest.pop("source_assurance")
    runtime = _AcceptedRuntime(manifest)

    with pytest.raises(
        WebProductRuntimeError, match="accepted Web assurance evidence is incomplete"
    ):
        runtime.get_manifest("legacy-accepted-web")

    with pytest.raises(
        WebProductRuntimeError, match="accepted Web assurance evidence is incomplete"
    ):
        runtime.recover_finalizing(
            "legacy-accepted-web",
            token="unused",
            now=datetime(2026, 8, 17, 0, 0, tzinfo=timezone.utc),
        )


def test_accepted_manifest_with_missing_gate_receipt_fails_closed() -> None:
    manifest = _accepted_manifest()
    manifest["security_evidence"] = {"status": "FAIL"}
    runtime = _AcceptedRuntime(manifest)

    with pytest.raises(
        WebProductRuntimeError, match="accepted Web assurance evidence is incomplete"
    ):
        runtime.get_state("legacy-accepted-web")

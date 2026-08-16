"""Regression coverage for accepted Web manifests that predate source assurance."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, cast

import pytest

from services.integrations.web_product_runtime import WebProductRuntimeError
from services.integrations.web_product_runtime_recovery import RecoverableWebProductRuntime


class _AcceptedRuntime(RecoverableWebProductRuntime):
    def __init__(self, manifest: dict[str, object]) -> None:
        self._connection = sqlite3.connect(":memory:")
        self._connection.row_factory = sqlite3.Row
        self._connection.execute(
            "CREATE TABLE web_product_requests ("
            "request_id TEXT PRIMARY KEY, principal_id TEXT NOT NULL, "
            "tenant_id TEXT NOT NULL, status TEXT NOT NULL, "
            "job_id TEXT NOT NULL, manifest_json TEXT)"
        )
        self._connection.execute(
            "CREATE TABLE web_product_closure ("
            "request_id TEXT PRIMARY KEY, terminal_status TEXT NOT NULL, "
            "reason TEXT NOT NULL, terminal_at TEXT NOT NULL)"
        )
        self._connection.execute(
            "INSERT INTO web_product_requests VALUES (?, ?, ?, 'accepted', ?, ?)",
            (
                str(manifest["request_id"]),
                "user-web-1",
                "tenant-web-1",
                str(manifest["job_id"]),
                json.dumps(manifest, sort_keys=True, separators=(",", ":")),
            ),
        )
        self._connection.execute(
            "INSERT INTO web_product_closure VALUES (?, 'accepted', ?, ?)",
            (
                str(manifest["request_id"]),
                "legacy accepted record",
                datetime(2026, 8, 17, 0, 0, tzinfo=timezone.utc).isoformat(),
            ),
        )

    def _connect(self) -> sqlite3.Connection:
        return self._connection


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
    assurance = cast(dict[str, object], recovered["source_assurance"])
    assert assurance["passed"] is True


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

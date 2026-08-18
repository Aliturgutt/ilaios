"""Deterministic BrowserQA adapter for exact local Chromium E2E evidence.

This adapter does not launch a browser and cannot replace the governed browser
tool/egress boundary. It validates an artifact produced by the existing Web
Factory Browser E2E workflow and makes that exact evidence consumable by the
canonical BrowserQA agent through GovernedRuntime.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

BROWSER_EVIDENCE_PROVIDER_ID = "ilaios.provider.browser-evidence.v1"
BROWSER_EVIDENCE_ADAPTER_KIND = "ilaios.runtime.browser-evidence.v1"
BROWSER_EVIDENCE_CAPABILITY = "web.verify"


class BrowserEvidenceAdapterError(RuntimeError):
    """Browser evidence is missing, stale, malformed, or outside the trusted root."""


class BrowserEvidenceRuntimeAdapter:
    def __init__(self, evidence_root: Path) -> None:
        self._root = evidence_root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def runtime_adapters(self) -> dict[str, Any]:
        return {BROWSER_EVIDENCE_ADAPTER_KIND: self.execute}

    def execute(self, payload: dict[str, Any]) -> dict[str, object]:
        raw_path = payload.get("evidence_path")
        source_sha = payload.get("source_sha")
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise BrowserEvidenceAdapterError("browser evidence path is required")
        if not isinstance(source_sha, str) or len(source_sha) != 40:
            raise BrowserEvidenceAdapterError("browser evidence requires exact source SHA")
        path = Path(raw_path).resolve()
        try:
            path.relative_to(self._root)
        except ValueError as exc:
            raise BrowserEvidenceAdapterError("browser evidence escapes trusted root") from exc
        if not path.is_file():
            raise BrowserEvidenceAdapterError("browser evidence artifact is unavailable")
        data = path.read_bytes()
        try:
            document = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BrowserEvidenceAdapterError("browser evidence JSON is malformed") from exc
        if not isinstance(document, dict):
            raise BrowserEvidenceAdapterError("browser evidence root must be an object")
        _validate_document(document, source_sha)
        browser = document["browser"]
        assert isinstance(browser, dict)
        return {
            "schema": "ilaios.browser-qa-evidence-attestation.v1",
            "source_sha": source_sha,
            "browser_evidence_sha256": hashlib.sha256(data).hexdigest(),
            "browser_engine": browser.get("engine"),
            "check_count": browser.get("check_count"),
            "verification_scope": document.get("verification_scope"),
            "public_production_proven": False,
            "browser_runtime_evidence": "PASS",
        }


def _validate_document(document: dict[str, Any], source_sha: str) -> None:
    if document.get("schema") != "ilaios.web.finished-product-browser-evidence.v2":
        raise BrowserEvidenceAdapterError("unexpected browser evidence schema")
    if document.get("source_head_sha") != source_sha:
        raise BrowserEvidenceAdapterError("browser evidence source SHA drifted")
    if document.get("adapter_id") != "web.product-runtime.v1":
        raise BrowserEvidenceAdapterError("browser evidence adapter identity drifted")
    if document.get("local_acceptance") is not True:
        raise BrowserEvidenceAdapterError("browser evidence lacks local acceptance")
    if document.get("browser_runtime_evidence") != "PASS":
        raise BrowserEvidenceAdapterError("browser runtime evidence did not pass")
    if document.get("public_production_proven") is not False:
        raise BrowserEvidenceAdapterError(
            "local BrowserQA evidence must not claim public production"
        )
    browser = document.get("browser")
    if not isinstance(browser, dict):
        raise BrowserEvidenceAdapterError("browser evidence payload is missing")
    required_pass = (
        "responsive",
        "navigation",
        "en_tr_content_parity",
        "accessibility",
        "seo",
        "security_headers",
        "functional_modules",
        "runtime",
    )
    if any(browser.get(field) != "PASS" for field in required_pass):
        raise BrowserEvidenceAdapterError("browser quality evidence is incomplete")
    check_count = browser.get("check_count")
    if not isinstance(check_count, int) or isinstance(check_count, bool) or check_count <= 0:
        raise BrowserEvidenceAdapterError("browser evidence contains no executed checks")
    if browser.get("console_errors") != 0 or browser.get("page_errors") != 0:
        raise BrowserEvidenceAdapterError("browser evidence contains runtime errors")

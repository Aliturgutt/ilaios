from __future__ import annotations

from pathlib import Path

import pytest

from services.integrations.native_reference_receipt_runtime import native_receipt_evidence


def test_native_receipt_preserves_consistency_and_logo_lock_evidence() -> None:
    outcome: dict[str, object] = {
        "reference_consistency_passed": True,
        "reference_consistency_score": 0.91,
        "reference_consistency_evidence_digest": "a" * 64,
        "reference_consistency_provenance_hash": "b" * 64,
        "logo_asset_lock_applied": True,
        "logo_asset_lock_source_sha256": "c" * 64,
        "logo_asset_lock_evidence_digest": "d" * 64,
        "logo_asset_lock_provenance_hash": "e" * 64,
        "artifact_sha256": "f" * 64,
        "provider_cost_microusd": 123,
    }

    evidence = native_receipt_evidence(outcome)

    assert evidence["reference_consistency_passed"] is True
    assert evidence["reference_consistency_score"] == 0.91
    assert evidence["logo_asset_lock_applied"] is True
    assert evidence["logo_asset_lock_source_sha256"] == "c" * 64
    assert "artifact_sha256" not in evidence
    assert "provider_cost_microusd" not in evidence


def test_native_receipt_fails_closed_without_consistency_pass() -> None:
    with pytest.raises(RuntimeError, match="lacks consistency PASS evidence"):
        native_receipt_evidence({"reference_consistency_passed": False})


def test_desktop_composition_uses_receipt_preserving_native_runtime() -> None:
    composition = (
        Path(__file__).resolve().parents[1]
        / "services"
        / "integrations"
        / "desktop_video_composition.py"
    ).read_text(encoding="utf-8")

    assert "ReceiptBoundNativeReferenceManagedDesktopVideoRuntime" in composition
    assert "NativeReferenceVerifiedManagedDesktopVideoRuntime(" not in composition

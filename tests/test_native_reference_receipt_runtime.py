from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from services.integrations.native_reference_receipt_runtime import native_receipt_evidence
from services.integrations.native_reference_verified_runtime import _native_provider_evidence
from services.reference_assets import ReferenceAssetRecord, ReferenceAssetRole


def _native_provider_fields() -> dict[str, object]:
    return {
        "provider_native_reference_url_used": True,
        "native_reference_mode": "input-references",
        "native_reference_count": 2,
        "native_reference_dispatch_count": 2,
        "native_reference_sha256s": ("1" * 64, "2" * 64),
        "native_reference_relay_released": True,
    }


def _record(role: ReferenceAssetRole, sha256: str) -> ReferenceAssetRecord:
    return ReferenceAssetRecord(
        asset_id=f"asset-{role.value}-{sha256[:8]}",
        principal_id="principal-1",
        tenant_id="tenant-1",
        sha256=sha256,
        mime_type="image/png",
        original_filename=f"{role.value}.png",
        width=64,
        height=64,
        size_bytes=128,
        role=role,
        instruction=None,
        created_at=datetime.now(timezone.utc),
    )


def test_native_receipt_preserves_provider_consistency_and_logo_lock_evidence() -> None:
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
        **_native_provider_fields(),
    }

    evidence = native_receipt_evidence(outcome)

    assert evidence["reference_consistency_passed"] is True
    assert evidence["reference_consistency_score"] == 0.91
    assert evidence["logo_asset_lock_applied"] is True
    assert evidence["logo_asset_lock_source_sha256"] == "c" * 64
    assert evidence["logo_asset_lock_repaired_artifact_sha256"] == "f" * 64
    assert evidence["provider_native_reference_url_used"] is True
    assert evidence["native_reference_mode"] == "input-references"
    assert evidence["native_reference_relay_released"] is True
    assert "artifact_sha256" not in evidence
    assert "provider_cost_microusd" not in evidence


def test_native_receipt_fails_closed_without_consistency_pass() -> None:
    with pytest.raises(RuntimeError, match="lacks consistency PASS evidence"):
        native_receipt_evidence({"reference_consistency_passed": False})


def test_native_receipt_fails_closed_without_provider_relay_evidence() -> None:
    with pytest.raises(RuntimeError, match="lacks provider relay evidence"):
        native_receipt_evidence({"reference_consistency_passed": True})


def test_native_receipt_fails_closed_on_invalid_repaired_artifact_digest() -> None:
    outcome = {
        "reference_consistency_passed": True,
        "logo_asset_lock_applied": True,
        "artifact_sha256": "not-a-digest",
        **_native_provider_fields(),
    }
    with pytest.raises(RuntimeError, match="repaired artifact digest is invalid"):
        native_receipt_evidence(outcome)


def test_native_provider_evidence_uses_input_references_for_seedance() -> None:
    records = (
        _record(ReferenceAssetRole.PRODUCT, "1" * 64),
        _record(ReferenceAssetRole.LOGO, "2" * 64),
    )

    evidence = _native_provider_evidence(
        records,
        model_id="bytedance/seedance-2.0-fast",
        generated_shot_count=2,
    )

    assert evidence["provider_native_reference_url_used"] is True
    assert evidence["native_reference_mode"] == "input-references"
    assert evidence["native_reference_count"] == 2
    assert evidence["native_reference_dispatch_count"] == 2
    assert evidence["native_reference_relay_released"] is True


def test_native_provider_evidence_gives_frame_images_precedence() -> None:
    records = (
        _record(ReferenceAssetRole.PRODUCT, "1" * 64),
        _record(ReferenceAssetRole.FIRST_FRAME, "2" * 64),
        _record(ReferenceAssetRole.LAST_FRAME, "3" * 64),
    )

    evidence = _native_provider_evidence(
        records,
        model_id="bytedance/seedance-2.0-fast",
        generated_shot_count=1,
    )

    assert evidence["provider_native_reference_url_used"] is True
    assert evidence["native_reference_mode"] == "frame-images"
    assert evidence["native_reference_count"] == 2
    assert evidence["native_reference_sha256s"] == ("2" * 64, "3" * 64)


def test_native_provider_evidence_preserves_private_brief_fallback() -> None:
    records = (_record(ReferenceAssetRole.PRODUCT, "1" * 64),)

    evidence = _native_provider_evidence(
        records,
        model_id="vendor/unproven-video-model",
        generated_shot_count=1,
    )

    assert evidence["provider_native_reference_url_used"] is False
    assert evidence["native_reference_mode"] == "private-multimodal-brief-fallback"
    assert evidence["native_reference_count"] == 0
    assert evidence["native_reference_dispatch_count"] == 0


def test_native_consistency_qa_is_pinned_to_supported_free_multimodal_model() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "services"
        / "integrations"
        / "native_reference_receipt_runtime.py"
    ).read_text(encoding="utf-8")

    assert '_NATIVE_CONSISTENCY_MODEL_ID = "google/gemma-4-26b-a4b-it:free"' in source
    assert "OpenRouterReferenceConsistencyReviewer(" in source
    assert "_NATIVE_CONSISTENCY_MODEL_ID" in source.split(
        "OpenRouterReferenceConsistencyReviewer(", 1
    )[1]


def test_desktop_composition_uses_receipt_preserving_native_runtime() -> None:
    composition = (
        Path(__file__).resolve().parents[1]
        / "services"
        / "integrations"
        / "desktop_video_composition.py"
    ).read_text(encoding="utf-8")

    assert "ReceiptBoundNativeReferenceManagedDesktopVideoRuntime" in composition
    assert "NativeReferenceVerifiedManagedDesktopVideoRuntime(" not in composition

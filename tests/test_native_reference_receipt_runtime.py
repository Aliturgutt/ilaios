from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from services.integrations.native_reference_receipt_runtime import native_receipt_evidence
from services.integrations.native_reference_verified_runtime import _native_provider_evidence
from services.reference_assets import ReferenceAssetRole


def _native_provider_fields() -> dict[str, object]:
    return {
        "provider_native_reference_url_used": True,
        "native_reference_mode": "input-references",
        "native_reference_count": 2,
        "native_reference_dispatch_count": 2,
        "native_reference_sha256s": ("1" * 64, "2" * 64),
        "native_reference_relay_released": True,
    }


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


def test_native_provider_evidence_uses_input_references_for_seedance() -> None:
    records = (
        SimpleNamespace(role=ReferenceAssetRole.PRODUCT, sha256="1" * 64),
        SimpleNamespace(role=ReferenceAssetRole.LOGO, sha256="2" * 64),
    )

    evidence = _native_provider_evidence(  # type: ignore[arg-type]
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
        SimpleNamespace(role=ReferenceAssetRole.PRODUCT, sha256="1" * 64),
        SimpleNamespace(role=ReferenceAssetRole.FIRST_FRAME, sha256="2" * 64),
        SimpleNamespace(role=ReferenceAssetRole.LAST_FRAME, sha256="3" * 64),
    )

    evidence = _native_provider_evidence(  # type: ignore[arg-type]
        records,
        model_id="bytedance/seedance-2.0-fast",
        generated_shot_count=1,
    )

    assert evidence["provider_native_reference_url_used"] is True
    assert evidence["native_reference_mode"] == "frame-images"
    assert evidence["native_reference_count"] == 2
    assert evidence["native_reference_sha256s"] == ("2" * 64, "3" * 64)


def test_native_provider_evidence_preserves_private_brief_fallback() -> None:
    records = (SimpleNamespace(role=ReferenceAssetRole.PRODUCT, sha256="1" * 64),)

    evidence = _native_provider_evidence(  # type: ignore[arg-type]
        records,
        model_id="vendor/unproven-video-model",
        generated_shot_count=1,
    )

    assert evidence["provider_native_reference_url_used"] is False
    assert evidence["native_reference_mode"] == "private-multimodal-brief-fallback"
    assert evidence["native_reference_count"] == 0
    assert evidence["native_reference_dispatch_count"] == 0


def test_desktop_composition_uses_receipt_preserving_native_runtime() -> None:
    composition = (
        Path(__file__).resolve().parents[1]
        / "services"
        / "integrations"
        / "desktop_video_composition.py"
    ).read_text(encoding="utf-8")

    assert "ReceiptBoundNativeReferenceManagedDesktopVideoRuntime" in composition
    assert "NativeReferenceVerifiedManagedDesktopVideoRuntime(" not in composition

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest

from src.video_automation.golden_delivery_evidence import (
    GoldenDeliveryEvidenceError,
    GoldenDeliveryReceipt,
)


_REQUIRED_VISUALS = frozenset(
    {"stock_footage", "visual_explainer", "chart", "kinetic_text", "transition"}
)
_REQUIRED_QA = frozenset({"technical", "visual", "audio", "brand"})


def _receipt(tmp_path: Path, **overrides: object) -> GoldenDeliveryReceipt:
    artifact = tmp_path / "final.mp4"
    artifact.write_bytes(b"real-finished-artifact-evidence")
    values: dict[str, object] = {
        "job_id": "job-golden-documentary",
        "final_mp4_path": str(artifact),
        "final_mp4_sha256": sha256(artifact.read_bytes()).hexdigest(),
        "stock_provider": "wikimedia",
        "stock_source_url": "https://commons.wikimedia.org/wiki/File:Example.webm",
        "stock_license_name": "CC BY-SA 4.0",
        "visual_features": _REQUIRED_VISUALS,
        "narration_present": True,
        "sound_effects_present": True,
        "music_present": True,
        "ducked_music_frames": 2400,
        "word_synced_captions_present": True,
        "qa_domains_passed": _REQUIRED_QA,
    }
    values.update(overrides)
    return GoldenDeliveryReceipt(**values)  # type: ignore[arg-type]


def test_golden_delivery_receipt_accepts_complete_evidence(tmp_path: Path) -> None:
    receipt = _receipt(tmp_path)
    assert receipt.visual_features == _REQUIRED_VISUALS
    assert receipt.qa_domains_passed == _REQUIRED_QA
    assert receipt.ducked_music_frames > 0


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("visual_features", frozenset({"stock_footage"}), "missing visual evidence"),
        ("narration_present", False, "requires narration evidence"),
        ("sound_effects_present", False, "requires SFX evidence"),
        ("music_present", False, "requires music evidence"),
        ("ducked_music_frames", 0, "music-ducking evidence"),
        ("word_synced_captions_present", False, "word-synced caption evidence"),
        ("qa_domains_passed", frozenset({"technical"}), "missing QA evidence"),
    ],
)
def test_golden_delivery_receipt_fails_closed_on_missing_proof(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    with pytest.raises(GoldenDeliveryEvidenceError, match=message):
        _receipt(tmp_path, **{field: value})


def test_golden_delivery_receipt_rejects_tampered_mp4(tmp_path: Path) -> None:
    artifact = tmp_path / "final.mp4"
    artifact.write_bytes(b"first")
    digest = sha256(artifact.read_bytes()).hexdigest()
    artifact.write_bytes(b"tampered")

    with pytest.raises(GoldenDeliveryEvidenceError, match="checksum does not match"):
        _receipt(tmp_path, final_mp4_path=str(artifact), final_mp4_sha256=digest)


def test_golden_delivery_receipt_rejects_non_https_stock_provenance(
    tmp_path: Path,
) -> None:
    with pytest.raises(GoldenDeliveryEvidenceError, match="must use https"):
        _receipt(tmp_path, stock_source_url="http://example.test/stock")

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


def _receipt(
    tmp_path: Path,
    *,
    visual_features: frozenset[str] = _REQUIRED_VISUALS,
    narration_present: bool = True,
    sound_effects_present: bool = True,
    music_present: bool = True,
    ducked_music_frames: int = 2400,
    word_synced_captions_present: bool = True,
    qa_domains_passed: frozenset[str] = _REQUIRED_QA,
    stock_source_url: str = "https://commons.wikimedia.org/wiki/File:Example.webm",
    final_mp4_path: str | None = None,
    final_mp4_sha256: str | None = None,
) -> GoldenDeliveryReceipt:
    artifact = tmp_path / "final.mp4"
    if final_mp4_path is None:
        artifact.write_bytes(b"real-finished-artifact-evidence")
        resolved_path = str(artifact)
    else:
        resolved_path = final_mp4_path
    resolved_digest = final_mp4_sha256
    if resolved_digest is None:
        resolved_digest = sha256(Path(resolved_path).read_bytes()).hexdigest()
    return GoldenDeliveryReceipt(
        job_id="job-golden-documentary",
        final_mp4_path=resolved_path,
        final_mp4_sha256=resolved_digest,
        stock_provider="wikimedia",
        stock_source_url=stock_source_url,
        stock_license_name="CC BY-SA 4.0",
        visual_features=visual_features,
        narration_present=narration_present,
        sound_effects_present=sound_effects_present,
        music_present=music_present,
        ducked_music_frames=ducked_music_frames,
        word_synced_captions_present=word_synced_captions_present,
        qa_domains_passed=qa_domains_passed,
    )


def test_golden_delivery_receipt_accepts_complete_evidence(tmp_path: Path) -> None:
    receipt = _receipt(tmp_path)
    assert receipt.visual_features == _REQUIRED_VISUALS
    assert receipt.qa_domains_passed == _REQUIRED_QA
    assert receipt.ducked_music_frames > 0


def test_golden_delivery_receipt_requires_complete_visual_evidence(tmp_path: Path) -> None:
    with pytest.raises(GoldenDeliveryEvidenceError, match="missing visual evidence"):
        _receipt(tmp_path, visual_features=frozenset({"stock_footage"}))


def test_golden_delivery_receipt_requires_narration(tmp_path: Path) -> None:
    with pytest.raises(GoldenDeliveryEvidenceError, match="requires narration evidence"):
        _receipt(tmp_path, narration_present=False)


def test_golden_delivery_receipt_requires_sfx(tmp_path: Path) -> None:
    with pytest.raises(GoldenDeliveryEvidenceError, match="requires SFX evidence"):
        _receipt(tmp_path, sound_effects_present=False)


def test_golden_delivery_receipt_requires_music(tmp_path: Path) -> None:
    with pytest.raises(GoldenDeliveryEvidenceError, match="requires music evidence"):
        _receipt(tmp_path, music_present=False)


def test_golden_delivery_receipt_requires_ducking(tmp_path: Path) -> None:
    with pytest.raises(GoldenDeliveryEvidenceError, match="music-ducking evidence"):
        _receipt(tmp_path, ducked_music_frames=0)


def test_golden_delivery_receipt_requires_word_sync(tmp_path: Path) -> None:
    with pytest.raises(GoldenDeliveryEvidenceError, match="word-synced caption evidence"):
        _receipt(tmp_path, word_synced_captions_present=False)


def test_golden_delivery_receipt_requires_all_qa_domains(tmp_path: Path) -> None:
    with pytest.raises(GoldenDeliveryEvidenceError, match="missing QA evidence"):
        _receipt(tmp_path, qa_domains_passed=frozenset({"technical"}))


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

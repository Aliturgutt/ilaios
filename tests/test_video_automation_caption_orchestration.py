from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from src.video_automation.caption_policy import resolve_caption_policy
from src.video_automation.caption_post_processing import CaptionPostProcessor
from src.video_automation.caption_subtitle import CaptionCue
from src.video_automation.platform_profiles import PlatformProfileRegistry
from src.video_automation.request_manifest import (
    CaptionMode,
    EpisodeRequestManifest,
    EpisodeRequestManifestBuilder,
)
from src.video_automation.shot_request_planning import ShotGenerationRequest


class _FakeLocalRenderer:
    def __init__(self) -> None:
        self.calls = 0

    @property
    def renderer_id(self) -> str:
        return "fake-local-caption-renderer"

    def burn_in(self, *, clean: Path, subtitle: Path, output: Path) -> None:
        self.calls += 1
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(clean.read_bytes() + b"\nCAPTIONED\n" + subtitle.read_bytes())


def _manifest(mode: CaptionMode = CaptionMode.OFF) -> EpisodeRequestManifest:
    request = ShotGenerationRequest(
        request_id="request-001",
        idempotency_key="a" * 64,
        shot_id="episode-001-shot-01",
        source_beat_id="beat-01",
        prompt_text="shot: governed scene",
        duration_seconds=5.0,
        aspect_ratio="9:16",
        frames_per_second=24,
        output_count=1,
        seed=None,
        metadata={},
    )
    return EpisodeRequestManifestBuilder().build(
        "episode-001", [request], caption_mode=mode
    )


def _cues() -> tuple[CaptionCue, ...]:
    return (CaptionCue("cue-1", "Merhaba", 0.0, 2.0),)


def test_default_off_overrides_platform_caption_requirement() -> None:
    profile = PlatformProfileRegistry.default().get("instagram", "reels")
    decision = resolve_caption_policy(manifest=_manifest(), platform_profile=profile)
    assert decision.effective_enabled is False
    assert decision.reason == "user_or_default_off"


def test_auto_uses_explicit_platform_requirement() -> None:
    profiles = PlatformProfileRegistry.default()
    enabled = resolve_caption_policy(
        manifest=_manifest(CaptionMode.AUTO),
        platform_profile=profiles.get("tiktok", "vertical"),
    )
    disabled = resolve_caption_policy(
        manifest=_manifest(CaptionMode.AUTO),
        platform_profile=profiles.get("youtube", "long_form"),
    )
    assert enabled.effective_enabled is True
    assert disabled.effective_enabled is False


def test_off_returns_without_rendering_or_touching_clean_master(tmp_path: Path) -> None:
    clean = tmp_path / "clean.mp4"
    clean.write_bytes(b"clean-master")
    before = sha256(clean.read_bytes()).hexdigest()
    renderer = _FakeLocalRenderer()
    result = CaptionPostProcessor(renderer=renderer).process(
        manifest=_manifest(CaptionMode.OFF),
        platform_profile=PlatformProfileRegistry.default().get("tiktok", "vertical"),
        clean_master_path=clean,
        cues=_cues(),
        timing_source="script",
        output_directory=tmp_path / "out",
    )
    assert result is None
    assert renderer.calls == 0
    assert sha256(clean.read_bytes()).hexdigest() == before
    assert not (tmp_path / "out").exists()


def test_on_creates_local_variant_and_preserves_clean_master(tmp_path: Path) -> None:
    clean = tmp_path / "clean.mp4"
    clean.write_bytes(b"clean-master")
    before = sha256(clean.read_bytes()).hexdigest()
    renderer = _FakeLocalRenderer()
    result = CaptionPostProcessor(renderer=renderer).process(
        manifest=_manifest(CaptionMode.ON),
        platform_profile=None,
        clean_master_path=clean,
        cues=_cues(),
        timing_source="script",
        output_directory=tmp_path / "out",
    )
    assert result is not None
    assert renderer.calls == 1
    assert result.renderer_id == "fake-local-caption-renderer"
    assert result.clean_master_sha256 == before
    assert sha256(clean.read_bytes()).hexdigest() == before
    assert Path(result.captioned_video_path).read_bytes().startswith(b"clean-master")
    assert Path(result.captions.srt_path).exists()
    assert Path(result.captions.vtt_path).exists()


def test_auto_required_profile_creates_caption_variant(tmp_path: Path) -> None:
    clean = tmp_path / "clean.mp4"
    clean.write_bytes(b"clean-master")
    renderer = _FakeLocalRenderer()
    result = CaptionPostProcessor(renderer=renderer).process(
        manifest=_manifest(CaptionMode.AUTO),
        platform_profile=PlatformProfileRegistry.default().get("youtube", "shorts"),
        clean_master_path=clean,
        cues=_cues(),
        timing_source="script",
        output_directory=tmp_path / "out",
    )
    assert result is not None
    assert renderer.calls == 1

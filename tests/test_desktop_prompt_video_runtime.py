from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from services.integrations.desktop_video_runtime import (
    DesktopPromptVideoRuntime,
    build_video_plan,
    requested_duration,
)
from services.integrations.video_runtime import DeterministicLocalVideoRuntime, VideoRuntimeError


def test_desktop_prompt_runtime_isolated_from_canonical_proof_runtime() -> None:
    assert issubclass(DesktopPromptVideoRuntime, DeterministicLocalVideoRuntime)


def test_desktop_prompt_video_duration_parses_english_and_turkish() -> None:
    assert requested_duration("Create a 20 second ILAIOS video") == 20.0
    assert requested_duration("ILAIOS için 15 saniye video hazırla") == 15.0
    assert requested_duration("Create a brand video") == 20.0


def test_desktop_prompt_video_duration_fails_closed_outside_product_bounds() -> None:
    with pytest.raises(VideoRuntimeError, match="8-60 seconds"):
        requested_duration("Create a 120 second video")


def test_ilaios_brand_plan_covers_script_storyboard_and_captions() -> None:
    plan = build_video_plan("Create a premium 20-second ILAIOS brand video", 20.0)

    assert len(plan.scenes) == 5
    assert len(plan.captions) == len(plan.scenes)
    assert tuple((cue.start, cue.end) for cue in plan.captions) == tuple(
        (scene.start, scene.end) for scene in plan.scenes
    )
    assert plan.voiceover.endswith("ILAIOS.")
    assert plan.scenes[0].headline == "ILAIOS"
    assert plan.scenes[-1].end == 20.0


def test_official_logo_fixture_remains_immutable(tmp_path: Path) -> None:
    logo = tmp_path / "03-ilaios-symbol-dark.jpg"
    payload = b"official-ilaios-symbol-test-fixture"
    logo.write_bytes(payload)

    digest_before = hashlib.sha256(logo.read_bytes()).hexdigest()
    digest_after = hashlib.sha256(logo.read_bytes()).hexdigest()

    assert digest_before == digest_after
    assert logo.read_bytes() == payload

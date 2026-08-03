from __future__ import annotations

import pytest

from src.video_automation.continuity import CharacterContinuity, ContinuityState
from src.video_automation.prompt_compilation import (
    PromptCompilationError,
    PromptSection,
    ShotPromptCompiler,
    ShotPromptPackage,
    ShotPromptPolicy,
)
from src.video_automation.scene_planning import CinematicShot


def _shot(*, shot_id: str = "episode-001-shot-002") -> CinematicShot:
    return CinematicShot(
        shot_id=shot_id,
        sequence=2,
        source_beat_id="beat-001",
        text="The commander raises the scanner toward the sealed bulkhead.",
        duration_seconds=5.0,
        continuity_note="Preserve the commander's scar and black field suit.",
        previous_shot_id="episode-001-shot-001",
        next_shot_id="episode-001-shot-003",
    )


def _continuity(*, shot_id: str = "episode-001-shot-002") -> ContinuityState:
    return ContinuityState(
        shot_id=shot_id,
        characters=(
            CharacterContinuity(
                character_id="lead",
                identity="adult expedition commander",
                appearance="short dark hair and a scar above the left eyebrow",
                costume="black field suit",
            ),
        ),
        location="abandoned orbital station corridor",
        objects=("handheld scanner",),
        technology=("sealed bulkhead",),
        timeline="night cycle",
        lighting="cold blue emergency lights",
        visual_style="grounded cinematic science fiction",
        camera_state="slow forward tracking shot",
        scene_state="the commander approaches the sealed bulkhead",
        previous_shot_id="episode-001-shot-001",
    )


def test_default_policy_is_auditable_and_compact() -> None:
    policy = ShotPromptPolicy()
    assert policy.include_identifiers is True
    assert policy.include_empty_sections is False
    assert policy.section_separator == "\n"


def test_compile_preserves_approved_shot_text_and_timing() -> None:
    package = ShotPromptCompiler().compile(_shot(), _continuity())
    assert package.shot_id == "episode-001-shot-002"
    assert package.source_beat_id == "beat-001"
    assert package.duration_seconds == 5.0
    assert package.section_map()["shot"] == _shot().text
    assert package.section_map()["duration_seconds"] == "5"


def test_compile_preserves_every_structured_continuity_field() -> None:
    sections = ShotPromptCompiler().compile(_shot(), _continuity()).section_map()
    assert "id=lead" in sections["characters"]
    assert "scar above the left eyebrow" in sections["characters"]
    assert "costume=black field suit" in sections["characters"]
    assert sections["location"] == "abandoned orbital station corridor"
    assert sections["objects"] == "handheld scanner"
    assert sections["technology"] == "sealed bulkhead"
    assert sections["timeline"] == "night cycle"
    assert sections["lighting"] == "cold blue emergency lights"
    assert sections["visual_style"] == "grounded cinematic science fiction"
    assert sections["camera_state"] == "slow forward tracking shot"
    assert sections["scene_state"] == "the commander approaches the sealed bulkhead"


def test_continuity_note_is_preserved_without_inference() -> None:
    package = ShotPromptCompiler().compile(_shot(), _continuity())
    assert package.section_map()["continuity_note"] == _shot().continuity_note


def test_section_order_is_deterministic() -> None:
    package = ShotPromptCompiler().compile(_shot(), _continuity())
    assert tuple(section.name for section in package.sections) == (
        "shot_id",
        "source_beat_id",
        "sequence",
        "duration_seconds",
        "shot",
        "characters",
        "location",
        "objects",
        "technology",
        "timeline",
        "lighting",
        "visual_style",
        "camera_state",
        "scene_state",
        "continuity_note",
    )


def test_prompt_text_uses_stable_name_value_lines() -> None:
    package = ShotPromptCompiler().compile(_shot(), _continuity())
    assert package.prompt_text.splitlines()[0] == "shot_id: episode-001-shot-002"
    assert "shot: The commander raises the scanner" in package.prompt_text


def test_custom_separator_is_applied_exactly() -> None:
    package = ShotPromptCompiler(
        ShotPromptPolicy(section_separator="\n---\n")
    ).compile(_shot(), _continuity())
    assert "\n---\nsource_beat_id:" in package.prompt_text


def test_identifiers_can_be_omitted_by_explicit_policy() -> None:
    package = ShotPromptCompiler(
        ShotPromptPolicy(include_identifiers=False)
    ).compile(_shot(), _continuity())
    names = tuple(section.name for section in package.sections)
    assert "shot_id" not in names
    assert "source_beat_id" not in names
    assert names[0] == "shot"


def test_empty_optional_sections_are_omitted_by_default() -> None:
    minimal = ContinuityState(shot_id="episode-001-shot-002")
    package = ShotPromptCompiler().compile(_shot(), minimal)
    names = tuple(section.name for section in package.sections)
    assert "characters" not in names
    assert "location" not in names
    assert "objects" not in names


def test_empty_optional_sections_can_be_declared_explicitly() -> None:
    minimal = ContinuityState(shot_id="episode-001-shot-002")
    package = ShotPromptCompiler(
        ShotPromptPolicy(include_empty_sections=True)
    ).compile(_shot(), minimal)
    sections = package.section_map()
    assert sections["characters"] == "none"
    assert sections["location"] == "none"
    assert sections["objects"] == "none"


def test_multiple_characters_keep_input_order() -> None:
    second = CharacterContinuity(
        character_id="guide",
        identity="maintenance android",
        appearance="weathered white shell with amber optics",
        costume="integrated utility harness",
    )
    state = ContinuityState(
        shot_id="episode-001-shot-002",
        characters=(_continuity().characters[0], second),
    )
    characters = ShotPromptCompiler().compile(_shot(), state).section_map()[
        "characters"
    ]
    assert characters.index("id=lead") < characters.index("id=guide")


def test_collection_values_keep_input_order() -> None:
    state = ContinuityState(
        shot_id="episode-001-shot-002",
        objects=("scanner", "access key"),
        technology=("bulkhead", "biometric lock"),
    )
    sections = ShotPromptCompiler().compile(_shot(), state).section_map()
    assert sections["objects"] == "scanner | access key"
    assert sections["technology"] == "bulkhead | biometric lock"


def test_mismatched_shot_identifiers_fail_closed() -> None:
    with pytest.raises(PromptCompilationError, match="must match"):
        ShotPromptCompiler().compile(
            _shot(),
            _continuity(shot_id="episode-001-shot-999"),
        )


def test_empty_separator_fails_closed() -> None:
    with pytest.raises(PromptCompilationError, match="section_separator"):
        ShotPromptPolicy(section_separator="")


def test_prompt_section_rejects_blank_values() -> None:
    with pytest.raises(PromptCompilationError, match="name"):
        PromptSection(" ", "value")
    with pytest.raises(PromptCompilationError, match="value"):
        PromptSection("name", " ")


def test_prompt_package_rejects_duplicate_section_names() -> None:
    with pytest.raises(PromptCompilationError, match="must be unique"):
        ShotPromptPackage(
            shot_id="shot-001",
            source_beat_id="beat-001",
            duration_seconds=5.0,
            sections=(PromptSection("shot", "one"), PromptSection("shot", "two")),
            prompt_text="shot: one\nshot: two",
        )


def test_compilation_is_repeatable_for_identical_inputs() -> None:
    compiler = ShotPromptCompiler()
    first = compiler.compile(_shot(), _continuity())
    second = compiler.compile(_shot(), _continuity())
    assert first == second

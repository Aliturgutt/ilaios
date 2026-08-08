"""Tests for deterministic ILAIOS script generation."""

from datetime import datetime, timezone

import pytest

from src.video_automation.models import (
    ResearchPacket,
    VideoFormat,
    VideoJob,
)
from src.video_automation.script_generation import (
    ScriptDraft,
    ScriptGenerationPipeline,
    ScriptGenerationPolicy,
    ScriptSectionDraft,
)

NOW = datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc)


def make_job(*, duration: int = 60) -> VideoJob:
    return VideoJob(
        job_id="job-1",
        project_id="project-1",
        topic="AI governance",
        objective="Create an educational video",
        target_audience="Engineering leaders",
        target_platforms=("youtube",),
        language="en",
        desired_duration_seconds=duration,
        video_format=VideoFormat.SHORT_FORM,
        aspect_ratio="9:16",
        content_style="technical",
        publishing_strategy="scheduled",
        provider_policy="test-default",
        budget_policy="no-paid-providers",
        approval_policy="manual-before-publish",
        created_at=NOW,
    )


def make_research(*, job_id: str = "job-1") -> ResearchPacket:
    return ResearchPacket(
        job_id=job_id,
        topic_summary="Research summary",
        verified_facts=("Fact A",),
        source_references=("source://a",),
        key_claims=("Claim A",),
    )


def make_draft() -> ScriptDraft:
    return ScriptDraft(
        hook="A strong hook",
        introduction="Introduction",
        sections=(
            ScriptSectionDraft(
                title="Section One",
                narration="Narration one",
                on_screen_text="On-screen one",
                estimated_duration_seconds=20,
            ),
            ScriptSectionDraft(
                title="Section Two",
                narration="Narration two",
                estimated_duration_seconds=25,
            ),
        ),
        cta="Subscribe",
        ending="Ending",
    )


def test_build_script_creates_canonical_video_script() -> None:
    pipeline = ScriptGenerationPipeline()

    script = pipeline.build_script(
        job=make_job(),
        research=make_research(),
        draft=make_draft(),
    )

    assert script.job_id == "job-1"
    assert script.hook == "A strong hook"
    assert script.estimated_duration_seconds == 45
    assert len(script.sections) == 2


def test_section_ids_are_deterministic() -> None:
    pipeline = ScriptGenerationPipeline()

    first = pipeline.build_script(
        job=make_job(),
        research=make_research(),
        draft=make_draft(),
    )
    second = pipeline.build_script(
        job=make_job(),
        research=make_research(),
        draft=make_draft(),
    )

    assert tuple(section.section_id for section in first.sections) == (
        "job-1:section:001",
        "job-1:section:002",
    )
    assert tuple(section.section_id for section in first.sections) == tuple(
        section.section_id for section in second.sections
    )


def test_pipeline_rejects_research_for_different_job() -> None:
    pipeline = ScriptGenerationPipeline()

    with pytest.raises(ValueError, match="research job_id"):
        pipeline.build_script(
            job=make_job(),
            research=make_research(job_id="job-other"),
            draft=make_draft(),
        )


def test_policy_can_require_cta() -> None:
    pipeline = ScriptGenerationPipeline(
        ScriptGenerationPolicy(require_cta=True)
    )
    draft = ScriptDraft(
        hook="Hook",
        introduction="Intro",
        sections=(
            ScriptSectionDraft(
                title="Section",
                narration="Narration",
                estimated_duration_seconds=10,
            ),
        ),
        ending="End",
        cta=None,
    )

    validation = pipeline.validate_inputs(
        job=make_job(),
        research=make_research(),
        draft=draft,
    )

    assert validation.passed is False
    assert validation.reasons == (
        "CTA is required by script generation policy",
    )


def test_pipeline_rejects_script_longer_than_requested_duration() -> None:
    pipeline = ScriptGenerationPipeline()

    with pytest.raises(ValueError, match="exceeds requested video duration"):
        pipeline.build_script(
            job=make_job(duration=30),
            research=make_research(),
            draft=make_draft(),
        )


def test_pipeline_requires_positive_total_section_duration() -> None:
    pipeline = ScriptGenerationPipeline()
    draft = ScriptDraft(
        hook="Hook",
        introduction="Intro",
        sections=(
            ScriptSectionDraft(
                title="Section",
                narration="Narration",
                estimated_duration_seconds=0,
            ),
        ),
        ending="End",
    )

    validation = pipeline.validate_inputs(
        job=make_job(),
        research=make_research(),
        draft=draft,
    )

    assert validation.passed is False
    assert validation.reasons == (
        "script section durations must total more than 0 seconds",
    )


def test_policy_rejects_too_many_sections() -> None:
    pipeline = ScriptGenerationPipeline(
        ScriptGenerationPolicy(
            minimum_sections=1,
            maximum_sections=1,
        )
    )

    validation = pipeline.validate_inputs(
        job=make_job(),
        research=make_research(),
        draft=make_draft(),
    )

    assert validation.passed is False
    assert validation.reasons == ("too many script sections: 2 > 1",)


def test_policy_requires_valid_section_bounds() -> None:
    with pytest.raises(ValueError, match="minimum_sections"):
        ScriptGenerationPolicy(minimum_sections=0)

    with pytest.raises(ValueError, match="maximum_sections"):
        ScriptGenerationPolicy(
            minimum_sections=3,
            maximum_sections=2,
        )


def test_draft_requires_sections() -> None:
    with pytest.raises(ValueError, match="sections must not be empty"):
        ScriptDraft(
            hook="Hook",
            introduction="Intro",
            sections=(),
            ending="End",
        )


def test_section_draft_rejects_negative_duration() -> None:
    with pytest.raises(ValueError, match="estimated_duration_seconds"):
        ScriptSectionDraft(
            title="Section",
            narration="Narration",
            estimated_duration_seconds=-1,
        )

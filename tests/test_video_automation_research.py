"""Tests for the ILAIOS Video Automation research pipeline."""

from datetime import datetime, timezone

import pytest

from src.video_automation.models import VideoFormat, VideoJob
from src.video_automation.research import (
    ResearchInput,
    ResearchPipeline,
    ResearchPolicy,
)

NOW = datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc)


def make_job() -> VideoJob:
    return VideoJob(
        job_id="job-1",
        project_id="project-1",
        topic="AI governance",
        objective="Create an educational video",
        target_audience="Engineering leaders",
        target_platforms=("youtube",),
        language="en",
        desired_duration_seconds=60,
        video_format=VideoFormat.SHORT_FORM,
        aspect_ratio="9:16",
        content_style="technical",
        publishing_strategy="scheduled",
        provider_policy="test-default",
        budget_policy="no-paid-providers",
        approval_policy="manual-before-publish",
        created_at=NOW,
    )


def test_default_policy_requires_fact_and_source() -> None:
    pipeline = ResearchPipeline()

    validation = pipeline.validate(
        ResearchInput(
            topic_summary="Summary",
            verified_facts=(),
            source_references=(),
        )
    )

    assert validation.passed is False
    assert len(validation.reasons) == 2


def test_valid_research_passes_default_policy() -> None:
    pipeline = ResearchPipeline()

    validation = pipeline.validate(
        ResearchInput(
            topic_summary="Summary",
            verified_facts=("Fact A",),
            source_references=("source://a",),
        )
    )

    assert validation.passed is True
    assert validation.reasons == ()


def test_pipeline_rejects_uncertain_claims_when_policy_requires() -> None:
    pipeline = ResearchPipeline(
        ResearchPolicy(
            minimum_verified_facts=1,
            minimum_source_references=1,
            reject_uncertain_claims=True,
        )
    )

    validation = pipeline.validate(
        ResearchInput(
            topic_summary="Summary",
            verified_facts=("Fact A",),
            source_references=("source://a",),
            uncertain_claims=("Uncertain A",),
        )
    )

    assert validation.passed is False
    assert validation.reasons == (
        "uncertain claims are not allowed by research policy",
    )


def test_pipeline_builds_research_packet_for_job() -> None:
    pipeline = ResearchPipeline()

    packet = pipeline.build_packet(
        job=make_job(),
        research=ResearchInput(
            topic_summary="AI governance summary",
            verified_facts=("Fact A", "Fact B"),
            source_references=("source://a", "source://b"),
            key_claims=("Claim A",),
            statistics=("42 percent",),
            relevant_dates=("2026-08-02",),
            entities=("Entity A",),
            risks=("Risk A",),
        ),
    )

    assert packet.job_id == "job-1"
    assert packet.topic_summary == "AI governance summary"
    assert packet.verified_facts == ("Fact A", "Fact B")
    assert packet.source_references == ("source://a", "source://b")


def test_pipeline_deduplicates_research_values_deterministically() -> None:
    pipeline = ResearchPipeline()

    packet = pipeline.build_packet(
        job=make_job(),
        research=ResearchInput(
            topic_summary="Summary",
            verified_facts=("Fact A", "Fact A", "Fact B"),
            source_references=("source://a", "source://a"),
            key_claims=("Claim A", "Claim A"),
        ),
    )

    assert packet.verified_facts == ("Fact A", "Fact B")
    assert packet.source_references == ("source://a",)
    assert packet.key_claims == ("Claim A",)


def test_pipeline_preserves_first_seen_order() -> None:
    pipeline = ResearchPipeline()

    packet = pipeline.build_packet(
        job=make_job(),
        research=ResearchInput(
            topic_summary="Summary",
            verified_facts=("Fact B", "Fact A", "Fact B"),
            source_references=("source://b", "source://a"),
        ),
    )

    assert packet.verified_facts == ("Fact B", "Fact A")
    assert packet.source_references == ("source://b", "source://a")


def test_build_packet_rejects_invalid_research() -> None:
    pipeline = ResearchPipeline()

    with pytest.raises(ValueError, match="research validation failed"):
        pipeline.build_packet(
            job=make_job(),
            research=ResearchInput(
                topic_summary="Summary",
                verified_facts=(),
                source_references=(),
            ),
        )


def test_research_input_rejects_blank_summary() -> None:
    with pytest.raises(ValueError, match="topic_summary"):
        ResearchInput(
            topic_summary=" ",
            verified_facts=("Fact A",),
            source_references=("source://a",),
        )


def test_pipeline_rejects_blank_fact() -> None:
    pipeline = ResearchPipeline()

    with pytest.raises(ValueError, match="verified fact"):
        pipeline.validate(
            ResearchInput(
                topic_summary="Summary",
                verified_facts=(" ",),
                source_references=("source://a",),
            )
        )


def test_policy_rejects_negative_thresholds() -> None:
    with pytest.raises(ValueError, match="minimum_verified_facts"):
        ResearchPolicy(minimum_verified_facts=-1)

    with pytest.raises(ValueError, match="minimum_source_references"):
        ResearchPolicy(minimum_source_references=-1)

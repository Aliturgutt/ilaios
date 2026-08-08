"""Deterministic script-generation layer for ILAIOS Video Automation."""

from __future__ import annotations

from dataclasses import dataclass

from .models import ResearchPacket, ScriptSection, VideoJob, VideoScript


def _validate_text(name: str, value: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{name} must not be empty")
    if value != value.strip():
        raise ValueError(f"{name} must not contain surrounding whitespace")


@dataclass(frozen=True, slots=True)
class ScriptSectionDraft:
    """Provider-neutral draft for one script section."""

    title: str
    narration: str
    on_screen_text: str | None = None
    estimated_duration_seconds: int = 0

    def __post_init__(self) -> None:
        _validate_text("title", self.title)
        _validate_text("narration", self.narration)
        if self.on_screen_text is not None:
            _validate_text("on_screen_text", self.on_screen_text)
        if self.estimated_duration_seconds < 0:
            raise ValueError("estimated_duration_seconds must be >= 0")


@dataclass(frozen=True, slots=True)
class ScriptDraft:
    """Provider-neutral script draft before canonical model materialization."""

    hook: str
    introduction: str
    sections: tuple[ScriptSectionDraft, ...]
    ending: str
    cta: str | None = None

    def __post_init__(self) -> None:
        _validate_text("hook", self.hook)
        _validate_text("introduction", self.introduction)
        _validate_text("ending", self.ending)
        if self.cta is not None:
            _validate_text("cta", self.cta)
        if not self.sections:
            raise ValueError("sections must not be empty")


@dataclass(frozen=True, slots=True)
class ScriptGenerationPolicy:
    """Deterministic constraints for generated scripts."""

    minimum_sections: int = 1
    maximum_sections: int = 20
    require_cta: bool = False
    require_research_evidence: bool = True

    def __post_init__(self) -> None:
        if self.minimum_sections < 1:
            raise ValueError("minimum_sections must be >= 1")
        if self.maximum_sections < self.minimum_sections:
            raise ValueError(
                "maximum_sections must be greater than or equal to minimum_sections"
            )


@dataclass(frozen=True, slots=True)
class ScriptValidation:
    """Validation result for a script draft."""

    passed: bool
    reasons: tuple[str, ...]


class ScriptGenerationPipeline:
    """Validate and materialize structured video scripts."""

    def __init__(self, policy: ScriptGenerationPolicy | None = None) -> None:
        self._policy = policy or ScriptGenerationPolicy()

    @property
    def policy(self) -> ScriptGenerationPolicy:
        return self._policy

    def validate_inputs(
        self,
        *,
        job: VideoJob,
        research: ResearchPacket,
        draft: ScriptDraft,
    ) -> ScriptValidation:
        """Validate generation inputs before creating the canonical script."""

        reasons: list[str] = []

        if research.job_id != job.job_id:
            reasons.append("research job_id does not match video job")

        section_count = len(draft.sections)
        if section_count < self._policy.minimum_sections:
            reasons.append(
                "insufficient script sections: "
                f"{section_count} < {self._policy.minimum_sections}"
            )
        if section_count > self._policy.maximum_sections:
            reasons.append(
                "too many script sections: "
                f"{section_count} > {self._policy.maximum_sections}"
            )

        if self._policy.require_cta and draft.cta is None:
            reasons.append("CTA is required by script generation policy")

        if self._policy.require_research_evidence:
            if not research.verified_facts:
                reasons.append("verified research facts are required")
            if not research.source_references:
                reasons.append("research source references are required")

        total_duration = sum(
            section.estimated_duration_seconds
            for section in draft.sections
        )
        if total_duration <= 0:
            reasons.append("script section durations must total more than 0 seconds")
        elif total_duration > job.desired_duration_seconds:
            reasons.append(
                "script section duration exceeds requested video duration"
            )

        return ScriptValidation(
            passed=not reasons,
            reasons=tuple(reasons),
        )

    def build_script(
        self,
        *,
        job: VideoJob,
        research: ResearchPacket,
        draft: ScriptDraft,
    ) -> VideoScript:
        """Create a canonical VideoScript with deterministic section identifiers."""

        validation = self.validate_inputs(
            job=job,
            research=research,
            draft=draft,
        )
        if not validation.passed:
            joined = "; ".join(validation.reasons)
            raise ValueError(f"script validation failed: {joined}")

        sections = tuple(
            ScriptSection(
                section_id=self._section_id(job.job_id, index),
                title=section.title,
                narration=section.narration,
                on_screen_text=section.on_screen_text,
                estimated_duration_seconds=section.estimated_duration_seconds,
            )
            for index, section in enumerate(draft.sections, start=1)
        )

        total_duration = sum(
            section.estimated_duration_seconds
            for section in sections
        )

        return VideoScript(
            job_id=job.job_id,
            hook=draft.hook,
            introduction=draft.introduction,
            sections=sections,
            cta=draft.cta,
            ending=draft.ending,
            estimated_duration_seconds=total_duration,
        )

    @staticmethod
    def _section_id(job_id: str, index: int) -> str:
        return f"{job_id}:section:{index:03d}"

"""Governed adapters for ILAIOS Video Factory prompting skills.

Every operation validates the corresponding first-party skill in the existing
runtime SkillRegistry before invoking provider-neutral domain logic. This module
does not create a second registry, select providers, dispatch models, ingest
reference bytes, or authorize side effects.
"""

from __future__ import annotations

from collections.abc import Iterable

from services.integrations.video_skill_governance import validate_video_skill
from services.runtime.routing import AgentProfile, SkillRegistry
from src.video_automation.video_prompting_skill_manifests import (
    VIDEO_PROMPTING_SKILLS,
)
from src.video_automation.video_prompting_skills import (
    ContinuityPlanner,
    ContinuityState,
    DirectorBrief,
    DirectorPlan,
    ModelCapabilityProfile,
    ModelRoutingAdvice,
    ModelRoutingAdvisor,
    ModelRoutingRequest,
    ReferenceAssetPlan,
    ReferenceAssetPlanner,
    ReferenceDirective,
    VideoDirector,
    VideoPromptComposer,
    VideoPromptRequest,
    VideoPromptResult,
)
from src.video_automation.video_skills import VideoSkillManifest

DIRECTOR_SKILL_ID = "ilaios.skill.video.director.plan"
PROMPT_SKILL_ID = "ilaios.skill.video.prompt.compose"
REFERENCE_ASSET_SKILL_ID = "ilaios.skill.video.reference-assets.plan"
MODEL_FIT_SKILL_ID = "ilaios.skill.video.model-fit.analyze"
CONTINUITY_SKILL_ID = "ilaios.skill.video.continuity.plan"


def _manifest(skill_id: str) -> VideoSkillManifest:
    try:
        return next(
            skill for skill in VIDEO_PROMPTING_SKILLS if skill.skill_id == skill_id
        )
    except StopIteration as error:
        raise RuntimeError(f"missing canonical video prompting skill: {skill_id}") from error


class GovernedVideoPromptingSkills:
    """Validate and execute read-only prompting capabilities through one registry."""

    def __init__(
        self,
        registry: SkillRegistry,
        agent: AgentProfile,
        *,
        director: VideoDirector | None = None,
        prompt_composer: VideoPromptComposer | None = None,
        reference_planner: ReferenceAssetPlanner | None = None,
        routing_advisor: ModelRoutingAdvisor | None = None,
        continuity_planner: ContinuityPlanner | None = None,
    ) -> None:
        self._registry = registry
        self._agent = agent
        self._director = director or VideoDirector()
        self._prompt_composer = prompt_composer or VideoPromptComposer()
        self._reference_planner = reference_planner or ReferenceAssetPlanner()
        self._routing_advisor = routing_advisor or ModelRoutingAdvisor()
        self._continuity_planner = continuity_planner or ContinuityPlanner()

    def direct(self, brief: DirectorBrief) -> DirectorPlan:
        self._validate(DIRECTOR_SKILL_ID)
        return self._director.plan(brief)

    def compose_prompt(self, request: VideoPromptRequest) -> VideoPromptResult:
        self._validate(PROMPT_SKILL_ID)
        return self._prompt_composer.compose(request)

    def plan_references(
        self,
        directives: Iterable[ReferenceDirective],
    ) -> ReferenceAssetPlan:
        self._validate(REFERENCE_ASSET_SKILL_ID)
        return self._reference_planner.plan(directives)

    def advise_model_fit(
        self,
        request: ModelRoutingRequest,
        profiles: Iterable[ModelCapabilityProfile],
    ) -> ModelRoutingAdvice:
        """Return capability-fit advice; canonical routing/provider selection stays external."""
        self._validate(MODEL_FIT_SKILL_ID)
        return self._routing_advisor.advise(request, profiles)

    def build_continuity(
        self,
        *,
        continuity_id: str,
        invariants: Iterable[str],
        object_state: Iterable[str] = (),
        screen_direction: Iterable[str] = (),
        ending_state: str,
    ) -> ContinuityState:
        self._validate(CONTINUITY_SKILL_ID)
        return self._continuity_planner.build(
            continuity_id=continuity_id,
            invariants=invariants,
            object_state=object_state,
            screen_direction=screen_direction,
            ending_state=ending_state,
        )

    def _validate(self, skill_id: str) -> None:
        validate_video_skill(
            self._registry,
            self._agent,
            _manifest(skill_id),
        )

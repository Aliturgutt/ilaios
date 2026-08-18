"""Governed adapters for ILAIOS Video Factory prompting skills.

The facade validates each first-party skill in the existing runtime SkillRegistry,
then delegates to canonical Video Factory components. It intentionally contains no
second director, prompt compiler, continuity engine, reference store, or router.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from services.ai_governance import RoutingPolicy
from services.integrations.video_skill_governance import validate_video_skill
from services.provider_catalog import ProviderCatalogSnapshot
from services.provider_state import ProviderRuntimeSnapshot
from services.reference_assets import ReferenceAssetRecord
from services.routing_intelligence import (
    RoutingIntelligenceEngine,
    RoutingIntelligenceEvidence,
    RoutingIntelligenceRequest,
)
from services.runtime.routing import AgentProfile, SkillRegistry
from src.video_automation.continuity import (
    ContinuityState,
    ContinuityTracker,
    ContinuityTransition,
    ContinuityUpdate,
)
from src.video_automation.creative_direction_execution import (
    CinematographyExecutionResult,
    CinematographyExecutor,
)
from src.video_automation.models import Shot
from src.video_automation.prompt_compilation import (
    ShotPromptCompiler,
    ShotPromptPackage,
)
from src.video_automation.scene_planning import CinematicShot
from src.video_automation.video_prompting_skill_manifests import (
    VIDEO_PROMPTING_SKILLS,
)
from src.video_automation.video_skills import (
    VIDEO_SKILLS,
    CreativeDirection,
    VideoSkillManifest,
)

DIRECTOR_SKILL_ID = "ilaios.skill.video.direction.cinematography"
PROMPT_SKILL_ID = "ilaios.skill.video.prompt.compose"
REFERENCE_ASSET_SKILL_ID = "ilaios.skill.video.reference-assets.inspect"
MODEL_FIT_SKILL_ID = "ilaios.skill.video.model-fit.analyze"
CONTINUITY_SKILL_ID = "ilaios.skill.video.continuity.track"

_SKILLS: tuple[VideoSkillManifest, ...] = (*VIDEO_SKILLS, *VIDEO_PROMPTING_SKILLS)


def _manifest(skill_id: str) -> VideoSkillManifest:
    try:
        return next(skill for skill in _SKILLS if skill.skill_id == skill_id)
    except StopIteration as error:
        raise RuntimeError(f"missing canonical video skill: {skill_id}") from error


class GovernedVideoPromptingSkills:
    """Govern existing canonical Video components behind governed skill checks."""

    def __init__(
        self,
        registry: SkillRegistry,
        agent: AgentProfile,
        *,
        director: CinematographyExecutor | None = None,
        prompt_compiler: ShotPromptCompiler | None = None,
        continuity: ContinuityTracker | None = None,
        routing_intelligence: RoutingIntelligenceEngine | None = None,
    ) -> None:
        self._registry = registry
        self._agent = agent
        self._director = director or CinematographyExecutor()
        self._prompt_compiler = prompt_compiler or ShotPromptCompiler()
        self._continuity = continuity or ContinuityTracker()
        self._routing_intelligence = routing_intelligence or RoutingIntelligenceEngine()

    def direct(
        self,
        shots: Sequence[Shot],
        direction: CreativeDirection,
    ) -> CinematographyExecutionResult:
        self._validate(DIRECTOR_SKILL_ID)
        return self._director.execute(shots, direction)

    def compose_prompt(
        self,
        shot: CinematicShot,
        continuity: ContinuityState,
    ) -> ShotPromptPackage:
        self._validate(PROMPT_SKILL_ID)
        return self._prompt_compiler.compile(shot, continuity)

    def inspect_references(
        self,
        records: Sequence[ReferenceAssetRecord],
    ) -> tuple[ReferenceAssetRecord, ...]:
        """Expose already-admitted immutable metadata without reading asset bytes."""
        self._validate(REFERENCE_ASSET_SKILL_ID)
        return tuple(records)

    def analyze_model_fit(
        self,
        *,
        catalog: ProviderCatalogSnapshot,
        runtime_state: ProviderRuntimeSnapshot,
        policy: RoutingPolicy,
        request: RoutingIntelligenceRequest,
        now: datetime,
    ) -> RoutingIntelligenceEvidence:
        """Return ranking evidence only; canonical routing remains authoritative."""
        self._validate(MODEL_FIT_SKILL_ID)
        return self._routing_intelligence.evaluate(
            catalog=catalog,
            runtime_state=runtime_state,
            policy=policy,
            request=request,
            now=now,
        )

    def start_continuity(self, state: ContinuityState) -> ContinuityState:
        self._validate(CONTINUITY_SKILL_ID)
        return self._continuity.start(state)

    def advance_continuity(
        self,
        previous: ContinuityState,
        *,
        shot_id: str,
        update: ContinuityUpdate | None = None,
    ) -> ContinuityTransition:
        self._validate(CONTINUITY_SKILL_ID)
        return self._continuity.advance(previous, shot_id=shot_id, update=update)

    def _validate(self, skill_id: str) -> None:
        validate_video_skill(self._registry, self._agent, _manifest(skill_id))

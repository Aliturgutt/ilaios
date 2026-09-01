"""Provider-backed Desktop finished-product runtime for the canonical Video Factory.

This adapter is the composition root that the Desktop one-prompt path was
missing. It binds the existing canonical shot planning, continuity, prompt
compilation, provider execution, polling, retrieval, technical validation,
semantic validation, episode assembly, final technical validation, evidence,
and delivery contracts into one fail-closed runtime.

The runtime deliberately has no motion-graphics or synthetic placeholder
fallback. If a real provider or independent semantic reviewer is unavailable,
the request fails instead of being reported as ACCEPTED.
"""

from __future__ import annotations

import json
import math
import shutil
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Protocol

from services.evidence import EvidenceStore
from services.governance import GovernedRuntimeGateway
from services.runtime import DurableGrantPolicy
from src.video_automation.assembled_output_technical_validation import (
    AssembledOutputTechnicalValidationCoordinator,
    AssembledOutputTechnicalValidationStatus,
)
from src.video_automation.continuity import (
    ContinuityState,
    ContinuityTracker,
    ContinuityUpdate,
)
from src.video_automation.episode_assembly_execution import (
    EpisodeAssemblyExecutionCoordinator,
    FfmpegEpisodeAssemblyExecutor,
)
from src.video_automation.episode_assembly_planning import EpisodeAssemblyPlanner
from src.video_automation.episode_assembly_request_planning import (
    EpisodeAssemblyOutputPolicy,
    EpisodeAssemblyRequestPlanner,
)
from src.video_automation.generated_asset_retrieval import (
    GeneratedAssetRetrievalCoordinator,
    GeneratedAssetRetrieverRegistry,
)
from src.video_automation.generation_batch_planning import (
    EpisodeGenerationBatchPlanner,
    GenerationBatchPolicy,
)
from src.video_automation.generation_dispatch_planning import (
    EpisodeGenerationDispatchPlanner,
    GenerationProviderBinding,
)
from src.video_automation.generation_execution_tracking import (
    EpisodeGenerationExecutionTracker,
    GenerationDispatchExecution,
)
from src.video_automation.generation_job_polling import (
    GenerationJobPoller,
    GenerationJobPollerRegistry,
    GenerationJobPollingCoordinator,
    ProviderJobObservation,
)
from src.video_automation.generation_result_ingestion import EpisodeGenerationResultIngester
from src.video_automation.generation_result_validation import (
    EpisodeGenerationResultValidator,
    GenerationAssetValidationObservation,
    GenerationAssetValidationStatus,
)
from src.video_automation.media_acquisition_orchestrator import (
    MediaAcquisitionGenerationOrchestrator,
)
from src.video_automation.media_technical_validation import (
    FfprobeMediaTechnicalProbe,
    MediaTechnicalProfile,
    MediaTechnicalValidationCoordinator,
    MediaTechnicalValidationStatus,
)
from src.video_automation.openrouter_perceptual_reviewer import (
    OpenRouterPerceptualReviewer,
)
from src.video_automation.openrouter_video_provider import (
    SEEDANCE_FREE_MODEL_ID,
    OpenRouterGeneratedAssetRetriever,
    OpenRouterVideoGenerationJobPoller,
    OpenRouterVideoGenerationProvider,
)
from src.video_automation.perceptual_review import (
    PerceptualReviewSubmission,
    admit_perceptual_reviews,
)
from src.video_automation.prompt_compilation import ShotPromptCompiler
from src.video_automation.provider_execution import ProviderExecutionOrchestrator
from src.video_automation.provider_registry import ProviderRegistry
from src.video_automation.providers import Provider
from src.video_automation.request_manifest import EpisodeRequestManifestBuilder
from src.video_automation.scene_planning import EpisodeBeat, ShotPlanner
from src.video_automation.shot_request_planning import (
    ShotGenerationPolicy,
    ShotGenerationRequestPlanner,
)

from .desktop_video_runtime import requested_duration
from .video_runtime import DeterministicLocalVideoRuntime, VideoRuntimeError

ObjectiveResolver = Callable[[str], str]


class SemanticVideoReviewer(Protocol):
    @property
    def reviewer_id(self) -> str: ...

    def review(
        self,
        *,
        video_path: Path,
        objective: str,
        artifact_sha256: str,
        producer_id: str,
        review_id: str,
    ) -> PerceptualReviewSubmission: ...


@dataclass(frozen=True, slots=True)
class ProviderCostEvidence:
    """Terminal provider-cost evidence admitted by the configured cost policy."""

    mode: str
    proven: bool
    zero: bool
    actual_microusd: int
    ceiling_microusd: int | None = None

    def __post_init__(self) -> None:
        if not self.mode.strip():
            raise VideoRuntimeError("provider cost evidence mode must not be blank")
        if not self.proven:
            raise VideoRuntimeError("provider cost evidence must be proven before acceptance")
        if self.actual_microusd < 0:
            raise VideoRuntimeError("provider actual cost must not be negative")
        if self.ceiling_microusd is not None:
            if self.ceiling_microusd < 0:
                raise VideoRuntimeError("provider cost ceiling must not be negative")
            if self.actual_microusd > self.ceiling_microusd:
                raise VideoRuntimeError("provider actual cost exceeded proven ceiling")
        if self.zero != (self.actual_microusd == 0):
            raise VideoRuntimeError("provider zero-cost evidence is inconsistent")


class ProviderCostEvidencePolicy(Protocol):
    """Fail-closed cost admission contract for one canonical provider runtime."""

    def validate_model_id(self, model_id: str) -> None: ...

    def verify(
        self, records: Sequence[GenerationDispatchExecution]
    ) -> ProviderCostEvidence: ...


class VerifiedFreeProviderCostPolicy:
    """Default policy: explicit free alias plus exact terminal provider cost zero."""

    def validate_model_id(self, model_id: str) -> None:
        if not model_id.endswith(":free"):
            raise VideoRuntimeError(
                "Desktop Video Factory requires an explicit free video model"
            )

    def verify(
        self, records: Sequence[GenerationDispatchExecution]
    ) -> ProviderCostEvidence:
        if not _zero_provider_cost_proven(records):
            raise VideoRuntimeError(
                "free provider execution lacks explicit zero-cost terminal evidence"
            )
        return ProviderCostEvidence(
            mode="verified-free",
            proven=True,
            zero=True,
            actual_microusd=0,
            ceiling_microusd=0,
        )


class _DelayedGenerationPoller:
    """Apply an explicit bounded polling cadence to the canonical poller."""

    def __init__(self, delegate: GenerationJobPoller, interval_seconds: float) -> None:
        if interval_seconds < 0:
            raise ValueError("poll interval must not be negative")
        self._delegate = delegate
        self._interval_seconds = interval_seconds

    @property
    def provider_id(self) -> str:
        return self._delegate.provider_id

    def poll(self, provider_job_id: str) -> ProviderJobObservation:
        if self._interval_seconds:
            time.sleep(self._interval_seconds)
        return self._delegate.poll(provider_job_id)


class ProviderBackedDesktopVideoRuntime(DeterministicLocalVideoRuntime):
    """Generate, validate, assemble, and deliver real provider-produced video."""

    PROVIDER_ID = "openrouter-video-free"
    PRODUCER_ID = "ilaios-provider-video-factory"

    def __init__(
        self,
        root: Path,
        grants: DurableGrantPolicy,
        governance: GovernedRuntimeGateway,
        evidence: EvidenceStore,
        *,
        objective_resolver: ObjectiveResolver,
        api_key: str,
        model_id: str = SEEDANCE_FREE_MODEL_ID,
        qa_model_id: str = "openrouter/free",
        resolution: str = "720p",
        poll_interval_seconds: float = 5.0,
        max_poll_rounds: int = 144,
        provider: Provider | None = None,
        poller: GenerationJobPoller | None = None,
        retriever: OpenRouterGeneratedAssetRetriever | None = None,
        reviewer: SemanticVideoReviewer | None = None,
        cost_policy: ProviderCostEvidencePolicy | None = None,
    ) -> None:
        super().__init__(root, grants, governance, evidence)
        if not api_key or api_key != api_key.strip():
            raise VideoRuntimeError("provider-backed video runtime requires API credentials")
        selected_cost_policy = cost_policy or VerifiedFreeProviderCostPolicy()
        selected_cost_policy.validate_model_id(model_id)
        if cost_policy is not None and not model_id.endswith(":free") and provider is None:
            raise VideoRuntimeError(
                "non-free Desktop Video Factory mode requires an injected governed provider"
            )
        if not qa_model_id.strip():
            raise VideoRuntimeError("semantic reviewer model must not be blank")
        if max_poll_rounds <= 0:
            raise VideoRuntimeError("max_poll_rounds must be positive")
        if poll_interval_seconds < 0:
            raise VideoRuntimeError("poll_interval_seconds must not be negative")
        self._objective_resolver = objective_resolver
        self._model_id = model_id
        self._resolution = resolution
        self._max_poll_rounds = max_poll_rounds
        self._cost_policy = selected_cost_policy
        self._provider = provider or OpenRouterVideoGenerationProvider(
            api_key,
            provider_name=self.PROVIDER_ID,
            default_resolution=resolution,
            generate_audio=True,
        )
        base_poller = poller or OpenRouterVideoGenerationJobPoller(
            api_key,
            provider_id=self.PROVIDER_ID,
        )
        self._poller = _DelayedGenerationPoller(base_poller, poll_interval_seconds)
        self._retriever = retriever or OpenRouterGeneratedAssetRetriever(
            api_key,
            provider_id=self.PROVIDER_ID,
        )
        self._reviewer = reviewer or OpenRouterPerceptualReviewer(
            api_key,
            qa_model_id,
        )

    def execute(
        self,
        *,
        request_id: str,
        job_id: str,
        grant_id: str,
        now: datetime,
    ) -> dict[str, object]:
        _runtime_identity("request_id", request_id)
        _runtime_identity("job_id", job_id)
        _runtime_identity("grant_id", grant_id)
        amount = self._governance.authorize_billable(request_id)
        started = time.monotonic()
        run_root: Path | None = None
        try:
            self._grants.authorize_and_record(
                grant_id,
                subject_id="worker-video",
                action="video.execute",
                resource=job_id,
                now=now,
            )
            objective = self._objective_resolver(job_id).strip()
            if not objective:
                raise VideoRuntimeError("provider-backed video objective is unavailable")
            duration = requested_duration(objective)
            run_root = self._root / request_id
            run_root.mkdir(parents=True, exist_ok=False)
            outcome = self._generate_finished_product(
                run_root=run_root,
                request_id=request_id,
                job_id=job_id,
                objective=objective,
                duration_seconds=duration,
            )
            final_path = Path(str(outcome["final_path"]))
            content = final_path.read_bytes()
            if not content:
                raise VideoRuntimeError("provider-backed final video is empty")
            artifact = self._evidence.put_artifact(content)
            if artifact.digest != outcome["artifact_sha256"]:
                raise VideoRuntimeError("final video digest changed after acceptance")
            provenance = self._evidence.append_provenance(
                job_id,
                artifact,
                "video.desktop.finished_product",
            )
            delivery = self._deliver(content, artifact.digest)
            latency_ms = int((time.monotonic() - started) * 1000)
            latency_budget_ms = 20 * 60 * 1000
            if latency_ms > latency_budget_ms:
                raise VideoRuntimeError("provider-backed video latency acceptance failed")
            qa = {
                "passed": True,
                "technical_passed": True,
                "semantic_passed": True,
                "semantic_score": outcome["semantic_score"],
                "semantic_threshold": outcome["semantic_threshold"],
                "generated_shot_count": outcome["generated_shot_count"],
                "provider_cost_mode": outcome["provider_cost_mode"],
                "provider_cost_proven": outcome["provider_cost_proven"],
                "provider_cost_zero": outcome["provider_cost_zero"],
                "provider_cost_microusd": outcome["provider_cost_microusd"],
                "provider_cost_ceiling_microusd": outcome[
                    "provider_cost_ceiling_microusd"
                ],
                "duration_seconds": outcome["duration_seconds"],
                "width": outcome["width"],
                "height": outcome["height"],
                "frame_rate": outcome["frame_rate"],
                "video_codec": outcome["video_codec"],
                "audio_codec": outcome["audio_codec"],
            }
            result: dict[str, object] = {
                "request_id": request_id,
                "job_id": job_id,
                "final_stage": "completed",
                "executed_stage_count": 13,
                "qa": qa,
                "artifact_digest": artifact.digest,
                "artifact_size": artifact.size,
                "provenance_record_hash": provenance.record_hash,
                "delivery": delivery,
                "publisher_boundary": "verified-local-delivery",
                "provider_boundary": self.PROVIDER_ID,
                "generation_mode": "provider-backed-cinematic-video",
                "provider_model_id": self._model_id,
                "provider_cost_mode": outcome["provider_cost_mode"],
                "provider_cost_proven": outcome["provider_cost_proven"],
                "provider_cost_zero": outcome["provider_cost_zero"],
                "provider_cost_microusd": outcome["provider_cost_microusd"],
                "provider_cost_ceiling_microusd": outcome[
                    "provider_cost_ceiling_microusd"
                ],
                "latency_ms": latency_ms,
                "latency_budget_ms": latency_budget_ms,
                "latency_passed": True,
                "metered_units": outcome["generated_shot_count"],
                "reserved_minor": 0,
                "governance_reserved_minor": amount,
                "actual_minor": 0,
                "cost_proven": True,
            }
            self._governance.reconcile_billable(
                request_id,
                actual_minor=0,
                status="executed",
                result=result,
            )
            return result
        except Exception:
            self._governance.reconcile_billable(
                request_id,
                actual_minor=0,
                status="failed",
            )
            raise
        finally:
            if run_root is not None and run_root.exists():
                shutil.rmtree(run_root, ignore_errors=True)

    def _generate_finished_product(
        self,
        *,
        run_root: Path,
        request_id: str,
        job_id: str,
        objective: str,
        duration_seconds: float,
    ) -> dict[str, object]:
        episode_id = f"{job_id}-episode"
        durations = _partition_duration(duration_seconds)
        prompts = _shot_prompts(objective, len(durations))
        beats = tuple(
            EpisodeBeat(
                beat_id=f"{episode_id}-beat-{index:03d}",
                text=prompt,
                duration_seconds=duration,
                continuity_note=(
                    "Preserve all identities, wardrobe, props, world state, lighting, "
                    "screen direction, and causal continuity unless the user objective "
                    "explicitly requests a change."
                ),
                shot_type="cinematic",
                subject="subjects explicitly requested by the user objective",
                action=f"realize cinematic shot {index} of {len(durations)}",
                environment="environment explicitly requested by the user objective",
                framing="cinematic framing appropriate to the requested shot",
                movement="physically plausible motivated camera movement",
                generation_prompt=prompt,
                required_provider_capability="video.generate",
            )
            for index, (duration, prompt) in enumerate(
                zip(durations, prompts, strict=True), start=1
            )
        )
        shot_plan = ShotPlanner().plan(beats, episode_id=episode_id)
        if len(shot_plan.shots) != len(durations):
            raise VideoRuntimeError("canonical shot planner changed the bounded shot count")

        compiler = ShotPromptCompiler()
        request_planner = ShotGenerationRequestPlanner(
            ShotGenerationPolicy(
                aspect_ratio="16:9",
                frames_per_second=24,
                output_count=1,
            )
        )
        tracker = ContinuityTracker()
        state: ContinuityState | None = None
        generation_requests = []
        for index, shot in enumerate(shot_plan.shots, start=1):
            if state is None:
                state = tracker.start(
                    ContinuityState(
                        shot_id=shot.shot_id,
                        timeline=f"shot {index} of {len(shot_plan.shots)}",
                        visual_style=_global_visual_context(objective),
                        camera_state=shot.generation_prompt,
                        scene_state=shot.generation_prompt,
                    )
                )
            else:
                transition = tracker.advance(
                    state,
                    shot_id=shot.shot_id,
                    update=ContinuityUpdate(
                        timeline=f"shot {index} of {len(shot_plan.shots)}",
                        camera_state=shot.generation_prompt,
                        scene_state=shot.generation_prompt,
                    ),
                )
                state = transition.current
            package = compiler.compile(shot, state)
            generation_requests.append(request_planner.plan(package))

        request_manifest = EpisodeRequestManifestBuilder().build(
            episode_id,
            tuple(generation_requests),
        )
        generation_plan = EpisodeGenerationBatchPlanner(
            GenerationBatchPolicy(max_requests_per_batch=1)
        ).plan(request_manifest)
        dispatch_plan = EpisodeGenerationDispatchPlanner(
            GenerationProviderBinding(
                provider_id=self.PROVIDER_ID,
                model_id=self._model_id,
                operation="video.generate",
                max_parallel_requests=1,
            )
        ).plan(generation_plan)

        provider_registry = ProviderRegistry((self._provider,))
        poller_registry = GenerationJobPollerRegistry((self._poller,))
        retriever_registry = GeneratedAssetRetrieverRegistry((self._retriever,))
        acquisition = MediaAcquisitionGenerationOrchestrator(
            provider_execution=ProviderExecutionOrchestrator(provider_registry),
            execution_tracker=EpisodeGenerationExecutionTracker(),
            polling=GenerationJobPollingCoordinator(poller_registry),
            result_ingester=EpisodeGenerationResultIngester(),
            asset_retrieval=GeneratedAssetRetrievalCoordinator(
                retriever_registry,
                run_root / "generated",
            ),
            max_poll_rounds=self._max_poll_rounds,
        ).execute(dispatch_plan)
        cost_evidence = self._cost_policy.verify(
            acquisition.final_execution_state.records
        )

        clip_profile = MediaTechnicalProfile(
            min_width=320,
            min_height=180,
            max_width=4320,
            max_height=4320,
            min_frames_per_second=20.0,
            max_frames_per_second=61.0,
            min_duration_seconds=3.0,
            max_duration_seconds=7.0,
            require_video_stream=True,
            allow_audio_stream=True,
            duration_tolerance_seconds=0.75,
        )
        clip_technical = MediaTechnicalValidationCoordinator(
            FfprobeMediaTechnicalProbe(timeout_seconds=30),
            clip_profile,
        ).validate(acquisition.retrieval_manifest)
        if clip_technical.status is not MediaTechnicalValidationStatus.PASSED:
            raise VideoRuntimeError("one or more generated clips failed technical QA")

        retrieved_by_id = {
            asset.asset_id: asset for asset in acquisition.retrieval_manifest.assets
        }
        dispatch_by_id = {
            dispatch.dispatch_id: dispatch for dispatch in dispatch_plan.dispatches
        }
        technical_by_id = {asset.asset_id: asset for asset in clip_technical.assets}
        semantic_observations: list[GenerationAssetValidationObservation] = []
        semantic_scores: list[float] = []
        for result_asset in acquisition.result_manifest.assets:
            retrieved = retrieved_by_id[result_asset.asset_id]
            technical = technical_by_id[result_asset.asset_id]
            if technical.status is not MediaTechnicalValidationStatus.PASSED:
                raise VideoRuntimeError("generated clip is not technically admissible")
            dispatch = dispatch_by_id[result_asset.dispatch_id]
            if len(dispatch.items) != 1:
                raise VideoRuntimeError("Desktop provider dispatch must contain one shot")
            shot_objective = dispatch.items[0].prompt_text
            review = self._reviewer.review(
                video_path=Path(retrieved.local_path),
                objective=shot_objective,
                artifact_sha256=retrieved.sha256_hex,
                producer_id=self.PRODUCER_ID,
                review_id=f"{request_id}-clip-{len(semantic_scores) + 1:03d}",
            )
            semantic_scores.append(review.score)
            semantic_observations.append(
                GenerationAssetValidationObservation(
                    asset_id=result_asset.asset_id,
                    status=(
                        GenerationAssetValidationStatus.ACCEPTED
                        if review.passed
                        else GenerationAssetValidationStatus.REJECTED
                    ),
                    checks=(
                        "technical-media-validation",
                        "independent-semantic-prompt-alignment",
                    ),
                    rejection_code=None if review.passed else "SEMANTIC_PROMPT_MISMATCH",
                    metadata={
                        "review_id": review.review_id,
                        "reviewer_id": review.reviewer_id,
                        "score": format(review.score, ".6f"),
                        "threshold": format(review.threshold, ".6f"),
                    },
                )
            )
        generation_validation = EpisodeGenerationResultValidator().validate(
            acquisition.result_manifest,
            tuple(semantic_observations),
        )
        if not generation_validation.all_accepted:
            raise VideoRuntimeError("generated shot semantic acceptance failed")

        assembly_plan = EpisodeAssemblyPlanner().plan(generation_validation)
        assembly_request = EpisodeAssemblyRequestPlanner().plan(
            assembly_plan,
            EpisodeAssemblyOutputPolicy(
                container_format="mp4",
                video_codec="libx264",
                audio_codec="aac",
                width=1920,
                height=1080,
                frame_rate=24,
            ),
        )
        assembly_artifact = EpisodeAssemblyExecutionCoordinator(
            FfmpegEpisodeAssemblyExecutor(timeout_seconds=900)
        ).execute(
            assembly_request,
            clip_technical,
            run_root / "assembled",
        )
        validation_artifact = replace(assembly_artifact, video_codec="h264")
        assembled_technical = AssembledOutputTechnicalValidationCoordinator(
            FfprobeMediaTechnicalProbe(timeout_seconds=30),
            frame_rate_tolerance=0.05,
        ).validate(validation_artifact)
        if assembled_technical.status is not AssembledOutputTechnicalValidationStatus.PASSED:
            raise VideoRuntimeError("assembled video failed final technical QA")
        observation = assembled_technical.observation
        if abs(observation.duration_seconds - duration_seconds) > 1.0:
            raise VideoRuntimeError("assembled video duration differs from user request")
        if observation.audio_stream_count < 1:
            raise VideoRuntimeError("assembled finished product is missing its audio stream")

        final_review = self._reviewer.review(
            video_path=Path(assembly_artifact.output_path),
            objective=objective,
            artifact_sha256=assembly_artifact.sha256_hex,
            producer_id=self.PRODUCER_ID,
            review_id=f"{request_id}-final",
        )
        admitted = admit_perceptual_reviews(
            (final_review,),
            artifact_sha256=assembly_artifact.sha256_hex,
            producer_id=self.PRODUCER_ID,
        )
        if len(admitted) != 1 or not final_review.passed:
            raise VideoRuntimeError("final video semantic acceptance failed")

        return {
            "final_path": assembly_artifact.output_path,
            "artifact_sha256": assembly_artifact.sha256_hex,
            "semantic_score": final_review.score,
            "semantic_threshold": final_review.threshold,
            "clip_semantic_min_score": min(semantic_scores),
            "generated_shot_count": len(shot_plan.shots),
            "provider_cost_mode": cost_evidence.mode,
            "provider_cost_proven": cost_evidence.proven,
            "provider_cost_zero": cost_evidence.zero,
            "provider_cost_microusd": cost_evidence.actual_microusd,
            "provider_cost_ceiling_microusd": cost_evidence.ceiling_microusd,
            "duration_seconds": observation.duration_seconds,
            "width": observation.width,
            "height": observation.height,
            "frame_rate": observation.frames_per_second,
            "video_codec": observation.video_codec,
            "audio_codec": observation.audio_codec or "none",
        }


class UnavailableProviderVideoRuntime(DeterministicLocalVideoRuntime):
    """Fail-closed runtime used when real provider credentials are unavailable."""

    def __init__(
        self,
        root: Path,
        grants: DurableGrantPolicy,
        governance: GovernedRuntimeGateway,
        evidence: EvidenceStore,
        *,
        reason: str,
    ) -> None:
        super().__init__(root, grants, governance, evidence)
        if not reason.strip():
            raise VideoRuntimeError("unavailable video runtime requires a reason")
        self._reason = reason.strip()

    def execute(
        self,
        *,
        request_id: str,
        job_id: str,
        grant_id: str,
        now: datetime,
    ) -> dict[str, object]:
        del request_id, job_id, grant_id, now
        raise VideoRuntimeError(self._reason)


def _partition_duration(duration: float) -> tuple[float, ...]:
    minimum_count = math.ceil(duration / 6.0)
    maximum_count = math.floor(duration / 4.0)
    if minimum_count > maximum_count:
        raise VideoRuntimeError("requested duration cannot form canonical 4-6 second shots")
    ideal = max(1, round(duration / 5.0))
    count = min(max(ideal, minimum_count), maximum_count)
    base = duration / count
    values = [base for _ in range(count)]
    values[-1] = duration - sum(values[:-1])
    if any(value < 4.0 or value > 6.0 for value in values):
        raise VideoRuntimeError("shot partition violated canonical duration bounds")
    return tuple(values)


def _shot_prompts(objective: str, count: int) -> tuple[str, ...]:
    normalized = "\n".join(line.strip() for line in objective.splitlines() if line.strip())
    if not normalized:
        raise VideoRuntimeError("video objective cannot be blank")
    global_context = _global_visual_context(normalized)
    chunks = _balanced_chunks(normalized, count)
    prompts = []
    for index, chunk in enumerate(chunks, start=1):
        prompts.append(
            "\n".join(
                (
                    "Create a real cinematic video shot, not a title card, slideshow, "
                    "motion-graphics placeholder, or text panel.",
                    f"This is shot {index} of {count} in one continuous finished film.",
                    "GLOBAL USER OBJECTIVE AND CONTINUITY CONTEXT:",
                    global_context,
                    "CURRENT SHOT-SPECIFIC SOURCE SEGMENT:",
                    chunk,
                    "Preserve character identity, wardrobe, props, environment, lighting, "
                    "screen direction, and causal state from adjacent shots. Show visible "
                    "scene action and environment requested by the user. Do not render the "
                    "instruction text on screen unless the user explicitly requested text.",
                )
            )
        )
    return tuple(prompts)


def _global_visual_context(objective: str) -> str:
    if len(objective) <= 4500:
        return objective
    return f"{objective[:2600]}\n[...middle objective retained by shot segments...]\n{objective[-1600:]}"


def _balanced_chunks(value: str, count: int) -> tuple[str, ...]:
    words = value.split()
    if not words:
        raise VideoRuntimeError("video objective cannot be blank")
    chunks: list[str] = []
    for index in range(count):
        start = math.floor(len(words) * index / count)
        end = math.floor(len(words) * (index + 1) / count)
        chunk = " ".join(words[start:end]).strip()
        if not chunk:
            chunk = value
        chunks.append(chunk)
    return tuple(chunks)


def _zero_provider_cost_proven(records: Sequence[GenerationDispatchExecution]) -> bool:
    if not records:
        return False
    for record in records:
        raw = record.metadata.get("usage_json")
        if not isinstance(raw, str) or not raw.strip():
            return False
        try:
            usage = json.loads(raw)
            if not isinstance(usage, dict):
                return False
            cost = Decimal(str(usage["cost"]))
        except (KeyError, TypeError, ValueError, InvalidOperation, json.JSONDecodeError):
            return False
        if cost != Decimal("0"):
            return False
    return True


def _runtime_identity(name: str, value: str) -> None:
    if not value or any(
        character
        not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        for character in value
    ):
        raise VideoRuntimeError(f"invalid {name}")

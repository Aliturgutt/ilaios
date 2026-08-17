"""Canonical M12 media acquisition and generation orchestration.

This module coordinates already-existing provider execution, execution-state
tracking, provider polling, result ingestion, and generated-asset retrieval.

It deliberately contains no provider-specific SDK logic. It does not select
providers, classify retryable failures, implement backoff policy, inspect media,
or persist registered assets into the canonical M13 asset store.

M27 owns cross-workflow retry/failure-recovery policy. M12 only enforces a
finite polling/acquisition boundary so provider work cannot wait indefinitely.
"""

from __future__ import annotations

from dataclasses import dataclass

from .generated_asset_retrieval import (
    EpisodeGeneratedAssetRetrievalManifest,
    GeneratedAssetRetrievalCoordinator,
)
from .generation_dispatch_planning import EpisodeGenerationDispatchPlan
from .generation_execution_tracking import (
    EpisodeGenerationExecutionState,
    EpisodeGenerationExecutionTracker,
)
from .generation_job_polling import GenerationJobPollingCoordinator
from .generation_result_ingestion import (
    EpisodeGenerationResultIngester,
    EpisodeGenerationResultManifest,
)
from .provider_execution import (
    EpisodeProviderExecutionReport,
    ProviderExecutionOrchestrator,
)


class MediaAcquisitionOrchestrationError(RuntimeError):
    """Raised when canonical M12 cannot complete acquisition safely."""


@dataclass(frozen=True, slots=True)
class MediaAcquisitionGenerationResult:
    """Normalized evidence produced by one successful M12 lifecycle."""

    dispatch_plan_id: str
    execution_report: EpisodeProviderExecutionReport
    final_execution_state: EpisodeGenerationExecutionState
    result_manifest: EpisodeGenerationResultManifest
    retrieval_manifest: EpisodeGeneratedAssetRetrievalManifest
    poll_rounds: int

    def __post_init__(self) -> None:
        if not self.dispatch_plan_id.strip():
            raise MediaAcquisitionOrchestrationError(
                "dispatch_plan_id must not be blank"
            )

        if self.poll_rounds < 0:
            raise MediaAcquisitionOrchestrationError(
                "poll_rounds must not be negative"
            )

        if self.execution_report.dispatch_plan_id != self.dispatch_plan_id:
            raise MediaAcquisitionOrchestrationError(
                "execution report does not belong to dispatch plan"
            )

        if self.final_execution_state.dispatch_plan_id != self.dispatch_plan_id:
            raise MediaAcquisitionOrchestrationError(
                "execution state does not belong to dispatch plan"
            )

        if self.result_manifest.dispatch_plan_id != self.dispatch_plan_id:
            raise MediaAcquisitionOrchestrationError(
                "result manifest does not belong to dispatch plan"
            )

        if self.retrieval_manifest.dispatch_plan_id != self.dispatch_plan_id:
            raise MediaAcquisitionOrchestrationError(
                "retrieval manifest does not belong to dispatch plan"
            )

        if not self.final_execution_state.is_terminal:
            raise MediaAcquisitionOrchestrationError(
                "final execution state must be terminal"
            )

        if self.final_execution_state.failed_count != 0:
            raise MediaAcquisitionOrchestrationError(
                "successful acquisition result cannot contain failed dispatches"
            )

        if self.final_execution_state.cancelled_count != 0:
            raise MediaAcquisitionOrchestrationError(
                "successful acquisition result cannot contain cancelled dispatches"
            )


class MediaAcquisitionGenerationOrchestrator:
    """Coordinate the canonical M12 generation/acquisition lifecycle."""

    def __init__(
        self,
        *,
        provider_execution: ProviderExecutionOrchestrator,
        execution_tracker: EpisodeGenerationExecutionTracker,
        polling: GenerationJobPollingCoordinator,
        result_ingester: EpisodeGenerationResultIngester,
        asset_retrieval: GeneratedAssetRetrievalCoordinator,
        max_poll_rounds: int,
    ) -> None:
        if max_poll_rounds <= 0:
            raise MediaAcquisitionOrchestrationError(
                "max_poll_rounds must be greater than zero"
            )

        self._provider_execution = provider_execution
        self._execution_tracker = execution_tracker
        self._polling = polling
        self._result_ingester = result_ingester
        self._asset_retrieval = asset_retrieval
        self._max_poll_rounds = max_poll_rounds

    def execute(
        self,
        dispatch_plan: EpisodeGenerationDispatchPlan,
    ) -> MediaAcquisitionGenerationResult:
        """Execute one complete provider-neutral M12 lifecycle.

        Steps:
        1. initialize immutable execution state;
        2. submit each planned dispatch through the existing provider executor;
        3. record every successful submission explicitly;
        4. poll active provider jobs for at most ``max_poll_rounds`` rounds;
        5. fail closed unless every dispatch succeeds;
        6. ingest terminal provider outputs;
        7. retrieve generated assets through registered retrieval adapters.
        """

        execution_state = self._execution_tracker.initialize(dispatch_plan)

        try:
            execution_report = self._provider_execution.execute(dispatch_plan)
        except Exception as exc:
            raise MediaAcquisitionOrchestrationError(
                f"provider submission stage failed: {_safe_error(exc)}"
            ) from exc

        if not execution_report.all_submitted:
            failures = tuple(
                _submission_failure_detail(submission)
                for submission in execution_report.submissions
                if not submission.success
            )
            raise MediaAcquisitionOrchestrationError(
                "provider submission failed: " + "; ".join(failures)
            )

        for submission in execution_report.submissions:
            execution_state = self._execution_tracker.apply(
                dispatch_plan,
                execution_state,
                submission.to_submitted_update(),
            )

        poll_rounds = 0

        while not execution_state.is_terminal:
            if poll_rounds >= self._max_poll_rounds:
                raise MediaAcquisitionOrchestrationError(
                    "generation polling exceeded max_poll_rounds before "
                    "execution became terminal"
                )

            poll_rounds += 1

            try:
                updates = self._polling.poll(
                    dispatch_plan,
                    execution_state,
                )
            except Exception as exc:
                raise MediaAcquisitionOrchestrationError(
                    f"generation polling failed in round {poll_rounds}: {_safe_error(exc)}"
                ) from exc

            for update in updates:
                execution_state = self._execution_tracker.apply(
                    dispatch_plan,
                    execution_state,
                    update,
                )

        if execution_state.failed_count:
            raise MediaAcquisitionOrchestrationError(
                "generation execution completed with failed dispatches"
            )

        if execution_state.cancelled_count:
            raise MediaAcquisitionOrchestrationError(
                "generation execution completed with cancelled dispatches"
            )

        try:
            result_manifest = self._result_ingester.ingest(execution_state)
        except Exception as exc:
            raise MediaAcquisitionOrchestrationError(
                f"generation result ingestion failed: {_safe_error(exc)}"
            ) from exc

        try:
            retrieval_manifest = self._asset_retrieval.retrieve(
                result_manifest,
                dispatch_plan,
            )
        except Exception as exc:
            raise MediaAcquisitionOrchestrationError(
                f"generated asset retrieval failed: {_safe_error(exc)}"
            ) from exc

        if retrieval_manifest.asset_count != len(result_manifest.assets):
            raise MediaAcquisitionOrchestrationError(
                "retrieval asset count does not match generation result asset count"
            )

        return MediaAcquisitionGenerationResult(
            dispatch_plan_id=dispatch_plan.dispatch_plan_id,
            execution_report=execution_report,
            final_execution_state=execution_state,
            result_manifest=result_manifest,
            retrieval_manifest=retrieval_manifest,
            poll_rounds=poll_rounds,
        )


def _submission_failure_detail(submission: object) -> str:
    dispatch_id = str(getattr(submission, "dispatch_id", "unknown"))
    code = str(getattr(submission, "error_code", None) or "provider_error")
    message = str(getattr(submission, "error_message", None) or "provider submission failed")
    return f"{dispatch_id}[{code}]={_bounded(message)}"


def _safe_error(exc: Exception) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    return _bounded(message)


def _bounded(value: str, *, limit: int = 400) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1] + "…"

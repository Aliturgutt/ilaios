"""Canonical scheduler integration for governed native video workers."""

from __future__ import annotations

from services.runtime.scheduler import SchedulingError, WorkerProfile
from src.media_model_governance import (
    NativeWorkerHardware,
    NativeWorkloadRequirements,
    evaluate_native_worker,
)

NATIVE_VIDEO_WORKER_CAPABILITY = "video.native.generate"


def build_native_video_worker_profile(
    *,
    hardware: NativeWorkerHardware,
    requirements: NativeWorkloadRequirements,
    max_concurrent_tasks: int = 1,
) -> WorkerProfile:
    """Return a canonical scheduler profile only for an eligible native worker."""

    decision = evaluate_native_worker(hardware, requirements)
    if not decision.eligible:
        reason = "; ".join(decision.reasons) or "native worker is ineligible"
        raise SchedulingError(f"native video worker registration blocked: {reason}")
    return WorkerProfile(
        worker_id=hardware.worker_id,
        capabilities=frozenset({NATIVE_VIDEO_WORKER_CAPABILITY}),
        max_concurrent_tasks=max_concurrent_tasks,
    )

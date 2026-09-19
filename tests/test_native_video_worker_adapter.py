from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from services.runtime.native_video_worker_adapter import (
    NATIVE_VIDEO_WORKER_CAPABILITY,
    build_native_video_worker_profile,
)
from services.runtime.scheduler import SchedulingError, WorkerScheduler
from src.media_model_governance import NativeWorkerHardware, NativeWorkloadRequirements


def _requirements() -> NativeWorkloadRequirements:
    return NativeWorkloadRequirements(required_vram_gb=12, required_ram_gb=32)


def test_ineligible_native_worker_cannot_enter_scheduler_pool() -> None:
    hardware = NativeWorkerHardware(
        worker_id="native-low-vram",
        gpu_name="test-gpu-4gb",
        vram_gb=4,
        ram_gb=16,
        cuda_available=True,
        healthy=True,
        free_vram_gb=4,
    )

    with pytest.raises(SchedulingError, match="registration blocked"):
        build_native_video_worker_profile(
            hardware=hardware,
            requirements=_requirements(),
        )


def test_eligible_native_worker_uses_existing_worker_scheduler() -> None:
    hardware = NativeWorkerHardware(
        worker_id="native-eligible",
        gpu_name="test-gpu",
        vram_gb=24,
        ram_gb=64,
        cuda_available=True,
        healthy=True,
        free_vram_gb=20,
    )
    scheduler = WorkerScheduler(lease_duration=timedelta(minutes=5))
    scheduler.register(
        build_native_video_worker_profile(
            hardware=hardware,
            requirements=_requirements(),
        )
    )

    lease = scheduler.schedule(
        "native-task-001",
        NATIVE_VIDEO_WORKER_CAPABILITY,
        now=datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc),
    )

    assert lease.worker_id == hardware.worker_id
    assert lease.fencing_token == 1

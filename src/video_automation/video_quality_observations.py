"""Translate immutable Video Factory evidence into independent QA observations.

This module does not create perceptual evidence.  It only converts deterministic
validation that already exists for the exact assembled artifact into the
canonical four-domain QA observation contract.
"""

from __future__ import annotations

from .assembled_output_technical_validation import (
    AssembledOutputTechnicalValidation,
    AssembledOutputTechnicalValidationStatus,
)
from .video_quality import QaObservationSource, VideoQaObservation
from .video_skills import QaDomain


def technical_observation_from_assembled_validation(
    validation: AssembledOutputTechnicalValidation,
    *,
    observer_id: str,
    producer_id: str,
) -> VideoQaObservation:
    """Bind deterministic assembled-output validation to the technical QA domain."""

    passed = validation.status is AssembledOutputTechnicalValidationStatus.PASSED
    return VideoQaObservation(
        observation_id=f"technical:{validation.validation_id}",
        domain=QaDomain.TECHNICAL,
        artifact_sha256=validation.sha256_hex,
        observer_id=observer_id,
        producer_id=producer_id,
        source=QaObservationSource.DETERMINISTIC_PROBE,
        score=1.0 if passed else 0.0,
        threshold=1.0,
        evidence_reference=validation.validation_id,
        provenance_reference=f"probe:{validation.probe_id}",
        repair_target=(
            None
            if passed
            else f"artifact:{validation.artifact_id}:technical"
        ),
    )

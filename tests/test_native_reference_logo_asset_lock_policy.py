from __future__ import annotations

from services.integrations.native_reference_verified_runtime import _logo_only_repairable
from src.video_automation.reference_consistency_review import ReferenceConsistencyReview


def _review(
    *,
    score: float,
    subject: float | None,
    product: float | None,
    logo: float | None,
) -> ReferenceConsistencyReview:
    return ReferenceConsistencyReview(
        reviewer_id="reviewer",
        criteria_version="ilaios.video.reference-consistency.v3",
        score=score,
        threshold=0.82,
        subject_score=subject,
        product_score=product,
        logo_score=logo,
        detail="visible evidence",
        repair_target="repair logo",
        reference_sha256s=("a" * 64,),
        reference_roles=("logo",),
        frame_sha256s=("b" * 64,),
        first_frame_sha256=None,
        last_frame_sha256=None,
    )


def test_logo_only_drift_is_asset_lock_repairable() -> None:
    assert _logo_only_repairable(
        _review(score=0.79, subject=0.91, product=0.90, logo=0.62)
    )


def test_product_drift_cannot_be_hidden_by_logo_overlay() -> None:
    assert not _logo_only_repairable(
        _review(score=0.70, subject=0.91, product=0.72, logo=0.62)
    )


def test_subject_drift_cannot_be_hidden_by_logo_overlay() -> None:
    assert not _logo_only_repairable(
        _review(score=0.70, subject=0.71, product=0.90, logo=0.62)
    )


def test_good_logo_never_triggers_asset_lock() -> None:
    assert not _logo_only_repairable(
        _review(score=0.91, subject=None, product=0.90, logo=0.88)
    )

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.desktop.e2e import provider_video_native_reference_finished_product_e2e as certification  # noqa: E402
from src.video_automation.openrouter_perceptual_reviewer import OpenRouterPerceptualReviewer  # noqa: E402
from src.video_automation.perceptual_review import PerceptualReviewSubmission  # noqa: E402

_ORIGINAL_REVIEW = OpenRouterPerceptualReviewer.review
_ORIGINAL_PRODUCT_PNG_BYTES = certification._product_png_bytes
_ORIGINAL_LOGO_PNG_BYTES = certification._logo_png_bytes
_semantic_reviews: list[PerceptualReviewSubmission] = []


def _provider_quality_product_png_bytes() -> bytes:
    """Build a deterministic premium product reference for the live provider proof.

    The old certification fixture was intentionally primitive: a flat rectangle,
    a cyan stripe, and a hard-edged orange circle. The latest real provider
    evidence showed that this source-of-truth was too weak for the semantic
    quality gate. Keep the fixture synthetic and repository-owned, but provide
    perspective, material depth, studio lighting, a bounded cyan light channel,
    and a clean inset emblem so the provider receives an unambiguous product
    identity rather than a diagram-like placeholder.
    """

    width, height = 640, 360
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            # Neutral studio backdrop with a restrained vertical luminance falloff.
            background = max(25, min(58, 48 - abs(y - 150) // 7))
            color = (background, background + 2, background + 5)

            # Soft elliptical floor shadow below the object.
            dx_shadow = (x - 326) / 214.0
            dy_shadow = (y - 292) / 27.0
            shadow = dx_shadow * dx_shadow + dy_shadow * dy_shadow
            if shadow <= 1.0:
                shade = int(22 + 14 * shadow)
                color = (shade, shade + 1, shade + 3)

            # Perspective product body: a subtly tapered premium appliance/tower.
            if 76 <= y <= 286:
                taper = (y - 76) / 210.0
                left = int(164 - 12 * taper)
                right = int(478 + 14 * taper)
                if left <= x <= right:
                    rel_x = (x - left) / max(1, right - left)
                    rel_y = (y - 76) / 210.0
                    # Matte graphite material with shaped light and edge falloff.
                    edge = min(rel_x, 1.0 - rel_x)
                    highlight = max(0.0, 1.0 - abs(rel_x - 0.36) / 0.34)
                    vertical = 1.0 - abs(rel_y - 0.38) * 0.28
                    base = 31 + int(18 * highlight * vertical) + int(7 * edge)
                    color = (base, base + 5, base + 10)

                    # Left bevel and right depth face reinforce apparent 3D geometry.
                    if rel_x < 0.055:
                        bevel = int(16 * (1.0 - rel_x / 0.055))
                        color = (max(20, base - bevel), max(24, base + 2 - bevel), max(28, base + 6 - bevel))
                    elif rel_x > 0.91:
                        depth = int(14 * ((rel_x - 0.91) / 0.09))
                        color = (max(18, base - depth), max(22, base + 1 - depth), max(27, base + 5 - depth))

                    # Fine horizontal material striation, low-amplitude and deterministic.
                    if 0.10 < rel_x < 0.88 and y % 17 == 0:
                        color = tuple(min(255, channel + 3) for channel in color)

            # Top bevel plane: brighter front-left edge, darker rear-right edge.
            if 162 <= x <= 479 and 68 <= y <= 87:
                top_left = 174 - (y - 68) // 2
                top_right = 468 + (y - 68) // 2
                if top_left <= x <= top_right:
                    t = (x - top_left) / max(1, top_right - top_left)
                    level = 61 - int(22 * t)
                    color = (level, level + 5, level + 9)

            # Recessed cyan vertical identity channel with bounded internal glow.
            if 301 <= x <= 338 and 96 <= y <= 267:
                edge_distance = min(x - 301, 338 - x)
                if edge_distance <= 3:
                    color = (18, 72, 78)
                else:
                    intensity = min(1.0, edge_distance / 15.0)
                    color = (
                        int(2 + 3 * intensity),
                        int(126 + 68 * intensity),
                        int(139 + 70 * intensity),
                    )
            if 296 <= x <= 343 and 91 <= y <= 272 and not (301 <= x <= 338 and 96 <= y <= 267):
                # Thin physical recess around the light channel.
                color = (23, 31, 37)

            # Clean inset orange emblem with a dark metal bezel and mild highlight.
            dx = x - 421
            dy = y - 132
            radius_sq = dx * dx + dy * dy
            if radius_sq <= 35 * 35:
                if radius_sq >= 30 * 30:
                    color = (24, 29, 34)
                else:
                    # Warm premium orange; highlight moves toward upper-left.
                    radial = max(0.0, 1.0 - radius_sq / float(30 * 30))
                    specular = max(0.0, 1.0 - ((dx + 9) ** 2 + (dy + 10) ** 2) / 380.0)
                    color = (
                        min(246, 211 + int(25 * radial) + int(10 * specular)),
                        min(139, 80 + int(29 * radial) + int(18 * specular)),
                        min(72, 31 + int(20 * radial) + int(8 * specular)),
                    )

            # Subtle feet/contact points ground the object in the studio scene.
            if (182 <= x <= 235 or 427 <= x <= 480) and 282 <= y <= 292:
                color = (22, 27, 31)

            rows.extend(color)
    return certification._rgb_png(width, height, bytes(rows))


def _provider_valid_logo_png_bytes() -> bytes:
    """Build the same synthetic logo at provider-valid reference dimensions.

    Seedance 2.0 reference inputs require both image dimensions to be at least
    300 px. The historical 160x64 certification fixture was valid PNG data but
    outside that provider boundary, which surfaced upstream as HTTP 500 instead
    of a useful 4xx validation error.
    """

    width, height = 480, 320
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            color = (17, 24, 39)
            if 48 <= x < 114 and 60 <= y < 260:
                color = (0, 194, 209)
            if 138 <= x < 432 and (90 <= y < 120 or 200 <= y < 230):
                color = (255, 255, 255)
            rows.extend(color)
    return certification._rgb_png(width, height, bytes(rows))


def _recording_review(
    self: OpenRouterPerceptualReviewer,
    *,
    video_path: Path,
    objective: str,
    artifact_sha256: str,
    producer_id: str,
    review_id: str,
) -> PerceptualReviewSubmission:
    review = _ORIGINAL_REVIEW(
        self,
        video_path=video_path,
        objective=objective,
        artifact_sha256=artifact_sha256,
        producer_id=producer_id,
        review_id=review_id,
    )
    _semantic_reviews.append(review)
    return review


def semantic_review_evidence(review: PerceptualReviewSubmission) -> dict[str, object]:
    """Return bounded, non-secret semantic-review evidence safe for CI artifacts."""
    return {
        "review_id": review.review_id,
        "reviewer_id": review.reviewer_id,
        "score": review.score,
        "threshold": review.threshold,
        "passed": review.passed,
        "repair_target": review.repair_target,
        "criteria_id": review.criteria_id,
        "criteria_version": review.criteria_version,
        "criteria_sha256": review.criteria_sha256,
        "provenance_reference": review.provenance_reference,
    }


def _select_failure_review(
    reviews: list[PerceptualReviewSubmission],
) -> PerceptualReviewSubmission | None:
    failed = [review for review in reviews if not review.passed]
    if failed:
        return failed[-1]
    if reviews:
        return reviews[-1]
    return None


def _semantic_review_stage(review: PerceptualReviewSubmission) -> str:
    return "final" if review.review_id.endswith("-final") else "generated-shot"


def _augment_failure_artifact(reviews: list[PerceptualReviewSubmission]) -> None:
    review = _select_failure_review(reviews)
    if review is None:
        return
    proof_root = Path(
        os.environ.get(
            "VIDEO_DESKTOP_NATIVE_REFERENCE_PROOF_DIR",
            "artifacts/video-desktop-native-reference-proof",
        )
    ).resolve()
    failure_path = proof_root / "failure.json"
    if not failure_path.is_file():
        return
    document = json.loads(failure_path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        return
    evidence = semantic_review_evidence(review)
    document["semantic_review_stage"] = _semantic_review_stage(review)
    document["semantic_review"] = evidence
    document["semantic_reviews"] = [
        semantic_review_evidence(item) for item in reviews if not item.passed
    ]
    failure_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "VIDEO_NATIVE_REFERENCE_SEMANTIC_REVIEW="
        + json.dumps(evidence, sort_keys=True, separators=(",", ":")),
        flush=True,
    )


def main() -> int:
    _semantic_reviews.clear()
    setattr(OpenRouterPerceptualReviewer, "review", _recording_review)
    setattr(certification, "_product_png_bytes", _provider_quality_product_png_bytes)
    setattr(certification, "_logo_png_bytes", _provider_valid_logo_png_bytes)
    try:
        return certification.main()
    except BaseException:
        _augment_failure_artifact(_semantic_reviews)
        raise
    finally:
        setattr(certification, "_product_png_bytes", _ORIGINAL_PRODUCT_PNG_BYTES)
        setattr(certification, "_logo_png_bytes", _ORIGINAL_LOGO_PNG_BYTES)
        setattr(OpenRouterPerceptualReviewer, "review", _ORIGINAL_REVIEW)


if __name__ == "__main__":
    raise SystemExit(main())

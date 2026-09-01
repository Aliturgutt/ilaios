from __future__ import annotations

import gc
import hashlib
import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from apps.desktop.e2e.video_finished_product_e2e import (
    _run_finished_product_acceptance,
)
from src.video_automation.ffmpeg_media_engine import FfmpegMediaEngine


REQUEST_ID = "desktop-video-real-render-e2e"
SAFE_STAGE_FILES = (
    "research.json",
    "script.json",
    "storyboard.json",
    "shot-plan.json",
    "asset-plan.json",
    "voice.wav",
    "music.wav",
    "captions.srt",
    "timeline.json",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _remove_runtime_private(path: Path) -> None:
    gc.collect()
    for attempt in range(5):
        try:
            shutil.rmtree(path)
            return
        except PermissionError:
            if attempt == 4:
                raise
            gc.collect()
            time.sleep(0.25 * (attempt + 1))


def main() -> int:
    artifact_root = Path(_required_env("ILAIOS_VIDEO_E2E_ARTIFACT_DIR")).resolve()
    source_revision = _required_env("ILAIOS_VIDEO_E2E_SOURCE_SHA")
    if len(source_revision) != 40 or any(ch not in "0123456789abcdef" for ch in source_revision):
        raise RuntimeError("ILAIOS_VIDEO_E2E_SOURCE_SHA must be an exact lowercase Git SHA")

    repo_root = Path(__file__).resolve().parents[3]
    logo = repo_root / "brand" / "assets" / "03-ilaios-symbol-dark.jpg"
    if not logo.is_file():
        raise RuntimeError("official ILAIOS brand logo is unavailable")
    logo_sha = _sha256(logo)

    if artifact_root.exists():
        shutil.rmtree(artifact_root)
    artifact_root.mkdir(parents=True, exist_ok=False)

    runtime_root = artifact_root / "runtime-private"
    runtime_root.mkdir(parents=True, exist_ok=False)
    _run_finished_product_acceptance(
        root=runtime_root,
        logo=logo,
        logo_hash_before=logo_sha,
    )

    run_root = runtime_root / "video" / REQUEST_ID
    rendered = run_root / "final.mp4"
    if not rendered.is_file() or rendered.stat().st_size <= 100_000:
        raise RuntimeError("verified finished-product MP4 is missing")
    rendered_sha = _sha256(rendered)

    finished_product = artifact_root / "finished-product.mp4"
    shutil.copy2(rendered, finished_product)
    finished_sha = _sha256(finished_product)
    if finished_sha != rendered_sha:
        raise RuntimeError("persisted MP4 digest does not match accepted rendered artifact")

    probe = FfmpegMediaEngine(timeout_seconds=60).probe(finished_product)
    video_stream = next(
        (stream for stream in probe.streams if stream.get("codec_type") == "video"),
        None,
    )
    audio_stream = next(
        (stream for stream in probe.streams if stream.get("codec_type") == "audio"),
        None,
    )
    if video_stream is None or audio_stream is None:
        raise RuntimeError("persisted finished product lacks audio/video streams")

    safe_stage_root = artifact_root / "stage-evidence"
    safe_stage_root.mkdir(parents=True, exist_ok=False)
    stage_receipts: list[dict[str, object]] = []
    for name in SAFE_STAGE_FILES:
        source = run_root / name
        if not source.is_file():
            raise RuntimeError(f"required safe stage evidence is missing: {name}")
        destination = safe_stage_root / name
        shutil.copy2(source, destination)
        stage_receipts.append(
            {
                "name": name,
                "bytes": destination.stat().st_size,
                "sha256": _sha256(destination),
            }
        )

    receipt = {
        "schema": "ilaios.video.local-finished-product-evidence.v1",
        "source_revision": source_revision,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "acceptance_manifest": "PASS",
        "execution_status": "ACCEPTED",
        "artifact": {
            "path": "finished-product.mp4",
            "sha256": finished_sha,
            "bytes": finished_product.stat().st_size,
            "duration_seconds": probe.duration_seconds,
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
            "video_codec": video_stream.get("codec_name"),
            "audio_codec": audio_stream.get("codec_name"),
        },
        "brand": {
            "canonical_logo": "brand/assets/03-ilaios-symbol-dark.jpg",
            "sha256": logo_sha,
            "immutable_during_render": True,
        },
        "stage_evidence": stage_receipts,
        "truth_boundary": (
            "This receipt proves the exact local Windows finished-product artifact "
            "produced by the governed CI E2E. It does not prove external provider "
            "generation, independent production perceptual review, publication, "
            "live production SLOs, or legal release."
        ),
    }
    (artifact_root / "artifact-receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # Do not publish runtime databases, test tokens, governance state, or other
    # private execution internals. Only the curated evidence above is uploadable.
    _remove_runtime_private(runtime_root)

    print(json.dumps(receipt, sort_keys=True))
    print("ILAIOS_DESKTOP_VIDEO_PERSISTED_EVIDENCE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

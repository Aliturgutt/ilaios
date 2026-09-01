"""Real deterministic local video execution through ILAIOS governance boundaries."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import time
from collections.abc import Mapping
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any

from services.evidence import EvidenceStore
from services.governance import GovernedRuntimeGateway
from services.runtime import DurableGrantPolicy
from src.video_automation.ffmpeg_media_engine import FfmpegMediaEngine
from src.video_automation.models import MediaAsset, MediaType, Timeline, TimelineItem
from src.video_automation.remotion_composition import RemotionCompositionAdapter
from src.video_automation.render_engine import LocalFfmpegRenderExecutor, RenderEngine
from src.video_automation.workflow_orchestrator import (
    VideoWorkflowOrchestrator,
    WorkflowGate,
    WorkflowStage,
    WorkflowStep,
)


class VideoRuntimeError(RuntimeError):
    """Raised when the real video chain cannot produce verified delivery."""


class DeterministicLocalVideoRuntime:
    """Composition root for local video, grants, FinOps, evidence, and delivery."""

    def __init__(
        self,
        root: Path,
        grants: DurableGrantPolicy,
        governance: GovernedRuntimeGateway,
        evidence: EvidenceStore,
    ) -> None:
        self._root = root
        self._grants = grants
        self._governance = governance
        self._evidence = evidence
        self._root.mkdir(parents=True, exist_ok=True)

    def execute(
        self,
        *,
        request_id: str,
        job_id: str,
        grant_id: str,
        now: datetime,
    ) -> dict[str, object]:
        for name, value in (
            ("request_id", request_id),
            ("job_id", job_id),
            ("grant_id", grant_id),
        ):
            if not value or any(
                character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
                for character in value
            ):
                raise VideoRuntimeError(f"invalid {name}")
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
            run_root = self._root / request_id
            run_root.mkdir(parents=True, exist_ok=False)
            execution = _LocalWorkflowExecution(run_root, job_id)
            workflow = VideoWorkflowOrchestrator().run(job_id, execution.steps())
            rendered = execution.rendered_path
            content = rendered.read_bytes()
            artifact = self._evidence.put_artifact(content)
            provenance = self._evidence.append_provenance(
                job_id, artifact, "video.local.rendered"
            )
            delivery = self._deliver(content, artifact.digest)
            latency_ms = int((time.monotonic() - started) * 1000)
            latency_budget_ms = 60_000
            if latency_ms > latency_budget_ms:
                raise VideoRuntimeError("local video latency acceptance failed")
            result: dict[str, object] = {
                "request_id": request_id,
                "job_id": job_id,
                "final_stage": workflow.progress.stage.value,
                "executed_stage_count": len(workflow.executed_stages),
                "qa": execution.qa,
                "artifact_digest": artifact.digest,
                "artifact_size": artifact.size,
                "provenance_record_hash": provenance.record_hash,
                "delivery": delivery,
                "publisher_boundary": "deterministic-local-delivery",
                "provider_boundary": "local-ffmpeg",
                "latency_ms": latency_ms,
                "latency_budget_ms": latency_budget_ms,
                "latency_passed": True,
                "metered_units": 1,
                "reserved_minor": amount,
                "actual_minor": amount,
            }
            self._governance.reconcile_billable(
                request_id, actual_minor=amount, status="executed", result=result
            )
            return result
        except Exception:
            self._governance.reconcile_billable(
                request_id, actual_minor=0, status="failed"
            )
            raise
        finally:
            if run_root is not None and run_root.exists():
                try:
                    shutil.rmtree(run_root)
                except OSError as error:
                    raise VideoRuntimeError(
                        "temporary video workspace cleanup failed"
                    ) from error

    def get_delivery(self, delivery_id: str) -> dict[str, object]:
        digest_prefix = delivery_id.removeprefix("delivery-")
        if (
            len(delivery_id) != 29
            or len(digest_prefix) != 20
            or any(character not in "0123456789abcdef" for character in digest_prefix)
        ):
            raise VideoRuntimeError("invalid delivery identity")
        path = self._root / "deliveries" / f"{delivery_id}.mp4"
        if not path.is_file():
            raise VideoRuntimeError("delivery is missing")
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        if delivery_id != f"delivery-{digest[:20]}":
            raise VideoRuntimeError("delivery integrity check failed")
        return {
            "delivery_id": delivery_id,
            "sha256": digest,
            "size": len(content),
            "path": str(path),
        }

    def _deliver(self, content: bytes, digest: str) -> dict[str, object]:
        delivery_id = f"delivery-{digest[:20]}"
        delivery_root = self._root / "deliveries"
        delivery_root.mkdir(parents=True, exist_ok=True)
        path = delivery_root / f"{delivery_id}.mp4"
        if path.exists() and path.read_bytes() != content:
            raise VideoRuntimeError("delivery identity collision")
        if not path.exists():
            path.write_bytes(content)
        return self.get_delivery(delivery_id)


class _LocalWorkflowExecution:
    def __init__(self, root: Path, job_id: str) -> None:
        self._root = root
        self._job_id = job_id
        self._rendered_path: Path | None = None
        self._qa: dict[str, object] | None = None

    @property
    def rendered_path(self) -> Path:
        if self._rendered_path is None:
            raise VideoRuntimeError("workflow did not render media")
        return self._rendered_path

    @property
    def qa(self) -> dict[str, object]:
        if self._qa is None:
            raise VideoRuntimeError("workflow did not perform technical QA")
        return self._qa

    def steps(self) -> tuple[WorkflowStep, ...]:
        return tuple(
            WorkflowStep(
                stage,
                WorkflowGate(),
                partial(self._execute_stage, stage),
                stage.value,
            )
            for stage in tuple(WorkflowStage)[1:]
        )

    def _execute_stage(
        self, stage: WorkflowStage, context: Mapping[str, Any]
    ) -> object:
        if stage is WorkflowStage.RENDERED:
            return self._render()
        if stage is WorkflowStage.TECHNICALLY_VALIDATED:
            return self._technical_validate()
        if stage is WorkflowStage.CONTENT_VALIDATED:
            if self.rendered_path.stat().st_size <= 0:
                raise VideoRuntimeError("rendered content is empty")
            return {"non_empty_media": True}
        if stage is WorkflowStage.PUBLISH_READY:
            return {"delivery_boundary_ready": True}
        if stage is WorkflowStage.COMPLETED:
            return {"completed_from": str(context[WorkflowStage.PUBLISH_READY.value])}
        return {"stage": stage.value, "mode": "deterministic-local"}

    def _render(self) -> dict[str, object]:
        source = self._root / "source.mp4"
        completed = subprocess.run(
            (
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                "color=c=blue:s=160x284:r=30:d=1",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=channel_layout=stereo:sample_rate=48000",
                "-t",
                "1",
                "-shortest",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                str(source),
            ),
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if completed.returncode != 0:
            raise VideoRuntimeError(f"local media generation failed: {completed.stderr}")
        source_content = source.read_bytes()
        asset = MediaAsset(
            "local-source",
            self._job_id,
            MediaType.VIDEO,
            str(source.resolve()),
            hashlib.sha256(source_content).hexdigest(),
            "local-test",
            "local://generated-source.mp4",
            True,
        )
        timeline = Timeline(
            self._job_id,
            (TimelineItem("timeline-item", asset.asset_id, 0.0, 1.0, 0),),
        )
        composition = RemotionCompositionAdapter().prepare(
            job_id=self._job_id,
            timeline=timeline,
            assets=(asset,),
            elements=(),
            output_directory=self._root / "composition",
            duration_seconds=1.0,
            fps=30,
            width=160,
            height=284,
        )
        artifact = RenderEngine(
            executor=LocalFfmpegRenderExecutor(timeout_seconds=60),
            probe_engine=FfmpegMediaEngine(timeout_seconds=60),
        ).render(
            job_id=self._job_id,
            composition=composition,
            output_path=self._root / "final.mp4",
        )
        self._rendered_path = Path(artifact.file_path)
        return {
            "sha256": artifact.checksum_sha256,
            "size": artifact.size_bytes,
            "codec": artifact.codec,
        }

    def _technical_validate(self) -> dict[str, object]:
        probe = FfmpegMediaEngine(timeout_seconds=60).probe(self.rendered_path)
        video = next(
            stream for stream in probe.streams if stream.get("codec_type") == "video"
        )
        audio = next(
            stream for stream in probe.streams if stream.get("codec_type") == "audio"
        )
        if video.get("codec_name") != "h264" or audio.get("codec_name") != "aac":
            raise VideoRuntimeError("rendered media codecs failed QA")
        self._qa = {
            "video_codec": video["codec_name"],
            "audio_codec": audio["codec_name"],
            "width": video["width"],
            "height": video["height"],
            "duration_seconds": probe.duration_seconds,
            "passed": True,
        }
        return self._qa

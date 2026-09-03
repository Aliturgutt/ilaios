"""Governed free-stock Desktop Video runtime.

This runtime reuses the canonical Desktop finished-product execution chain, but
replaces the synthetic background with one governed stock asset selected through
the existing provider-bound adapters. It performs no paid AI video generation.
"""

from __future__ import annotations

import hashlib
import subprocess
import time
from datetime import datetime
from pathlib import Path

from services.evidence import EvidenceStore
from services.governance import GovernedRuntimeGateway
from services.runtime import DurableGrantPolicy
from src.video_automation.governed_stock_composition import (
    GovernedStockCompositionInput,
    composition_input_from_selection,
    ffmpeg_stock_input_args,
    stock_visual_filter,
)
from src.video_automation.governed_stock_media_fetch import fetch_selected_stock_media
from src.video_automation.governed_stock_selection import GovernedStockSelector
from src.video_automation.workflow_orchestrator import (
    VideoWorkflowOrchestrator,
    WorkflowRunResult,
)

from .desktop_video_runtime import (
    ObjectiveResolver,
    _DesktopFinishedProductExecution,
    _validate_runtime_identity,
    _visual_filters,
    _windows_font,
)
from .video_runtime import DeterministicLocalVideoRuntime, VideoRuntimeError


class GovernedStockDesktopVideoRuntime(DeterministicLocalVideoRuntime):
    """Produce one finished MP4 from governed stock plus the canonical local chain."""

    PROVIDER_ID = "governed-public-stock"

    def __init__(
        self,
        root: Path,
        grants: DurableGrantPolicy,
        governance: GovernedRuntimeGateway,
        evidence: EvidenceStore,
        *,
        objective_resolver: ObjectiveResolver,
        brand_logo: Path,
        stock_selector: GovernedStockSelector,
    ) -> None:
        super().__init__(root, grants, governance, evidence)
        self._objective_resolver = objective_resolver
        self._brand_logo = brand_logo
        self._stock_selector = stock_selector

    def execute(
        self,
        *,
        request_id: str,
        job_id: str,
        grant_id: str,
        now: datetime,
    ) -> dict[str, object]:
        _validate_runtime_identity("request_id", request_id)
        _validate_runtime_identity("job_id", job_id)
        _validate_runtime_identity("grant_id", grant_id)
        amount = self._governance.authorize_billable(request_id)
        started = time.monotonic()
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
                raise VideoRuntimeError("governed stock video objective is unavailable")
            run_root = self._root / request_id
            run_root.mkdir(parents=True, exist_ok=False)
            selection = self._stock_selector.select(
                tenant_id=request_id,
                job_id=job_id,
                query=_stock_query(objective),
                media_types=frozenset({"video", "image"}),
            )
            fetched = fetch_selected_stock_media(
                selection.candidate,
                destination=run_root / "stock-media.bin",
            )
            composition = composition_input_from_selection(
                selection,
                media_path=fetched.path,
            )
            execution = _GovernedStockFinishedProductExecution(
                run_root,
                job_id,
                objective,
                self._brand_logo,
                composition,
            )
            workflow = execution.run_workflow()
            rendered = execution.rendered_path
            content = rendered.read_bytes()
            artifact = self._evidence.put_artifact(content)
            provenance = self._evidence.append_provenance(
                job_id,
                artifact,
                "video.desktop.governed_stock_finished_product",
            )
            delivery = self._deliver(content, artifact.digest)
            latency_ms = int((time.monotonic() - started) * 1000)
            latency_budget_ms = 180_000
            if latency_ms > latency_budget_ms:
                raise VideoRuntimeError("governed stock Desktop video latency acceptance failed")
            result: dict[str, object] = {
                "request_id": request_id,
                "job_id": job_id,
                "final_stage": workflow.progress.stage.value,
                "executed_stage_count": len(workflow.executed_stages),
                "qa": execution.qa,
                "stock_evidence": execution.stock_evidence,
                "artifact_digest": artifact.digest,
                "artifact_size": artifact.size,
                "provenance_record_hash": provenance.record_hash,
                "delivery": delivery,
                "publisher_boundary": "deterministic-local-delivery",
                "provider_boundary": self.PROVIDER_ID,
                "generation_mode": "governed-stock-finished-product",
                "paid_ai_video_generation": False,
                "latency_ms": latency_ms,
                "latency_budget_ms": latency_budget_ms,
                "latency_passed": True,
                "metered_units": 1,
                "reserved_minor": amount,
                "actual_minor": amount,
            }
            self._governance.reconcile_billable(
                request_id,
                actual_minor=amount,
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


class _GovernedStockFinishedProductExecution(_DesktopFinishedProductExecution):
    def __init__(
        self,
        root: Path,
        job_id: str,
        objective: str,
        brand_logo: Path,
        stock: GovernedStockCompositionInput,
    ) -> None:
        super().__init__(root, job_id, objective, brand_logo)
        self._stock = stock
        self._stock_evidence: dict[str, object] | None = None

    @property
    def stock_evidence(self) -> dict[str, object]:
        if self._stock_evidence is None:
            raise VideoRuntimeError("governed stock evidence is unavailable")
        return self._stock_evidence

    def run_workflow(self) -> WorkflowRunResult:
        return VideoWorkflowOrchestrator().run(self._job_id, self.steps())

    def _acquire_assets(self) -> dict[str, object]:
        payload = super()._acquire_assets()
        payload.update(
            {
                "stock_media_path": str(self._stock.media_path),
                "stock_media_sha256": self._stock.media_sha256,
                "stock_provider": self._stock.provider,
                "stock_source_url": self._stock.source_url,
                "stock_license_name": self._stock.license_name,
                "stock_creator": self._stock.creator,
                "stock_attribution_required": self._stock.attribution_required,
            }
        )
        return payload

    def _render(self, *, repair: bool) -> dict[str, object]:
        font = _windows_font()
        output = self._root / "final.mp4"
        text_filters = _visual_filters(self._plan, font, self._duration)
        logo_start = max(0.0, self._duration - 3.0)
        filter_complex = (
            f"[0:v]{stock_visual_filter()},{text_filters}[base];"
            "[1:v]scale=220:-2[logo];"
            "[base][logo]overlay=(W-w)/2:110:"
            f"enable='between(t,0,3)+between(t,{logo_start:.3f},{self._duration:.3f})'[v];"
            "[2:a]volume=1.0[voice];[3:a]volume=0.55[music];"
            "[voice][music]amix=inputs=2:duration=longest:dropout_transition=0[a]"
        )
        command = (
            "ffmpeg",
            "-y",
            "-v",
            "error",
            *ffmpeg_stock_input_args(self._stock),
            "-loop",
            "1",
            "-i",
            str(self._brand_logo),
            "-i",
            str(self._voice_path),
            "-i",
            str(self._music_path),
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-t",
            f"{self._duration:.3f}",
            "-r",
            "24",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast" if repair else "medium",
            "-crf",
            "20" if repair else "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-movflags",
            "+faststart",
            str(output),
        )
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=150,
        )
        if completed.returncode != 0 or not output.is_file():
            detail = completed.stderr[-500:] if completed.stderr else ""
            raise VideoRuntimeError(f"governed stock 1080p render failed: {detail}")
        self._rendered_path = output
        final_sha = hashlib.sha256(output.read_bytes()).hexdigest()
        self._stock_evidence = self._stock.evidence(final_mp4_sha256=final_sha)
        return {
            "path": str(output),
            "sha256": final_sha,
            "size": output.stat().st_size,
            "resolution": "1920x1080",
            "fps": 24,
            "repair_render": repair,
            "stock_provider": self._stock.provider,
            "stock_media_sha256": self._stock.media_sha256,
        }

    def _content_validate(self) -> dict[str, object]:
        result = super()._content_validate()
        if self._stock_evidence is None:
            raise VideoRuntimeError("governed stock final-artifact evidence is missing")
        final_sha = hashlib.sha256(self.rendered_path.read_bytes()).hexdigest()
        if self._stock_evidence.get("final_mp4_sha256") != final_sha:
            raise VideoRuntimeError("governed stock evidence is not bound to final MP4")
        result.update(
            {
                "governed_stock_present": True,
                "stock_provider": self._stock.provider,
                "stock_license_name": self._stock.license_name,
                "stock_final_artifact_bound": True,
            }
        )
        return result


def _stock_query(objective: str) -> str:
    query = " ".join(objective.split())[:160].strip()
    if not query:
        raise VideoRuntimeError("governed stock search query is empty")
    return query

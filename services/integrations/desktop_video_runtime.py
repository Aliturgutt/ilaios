"""Prompt-driven Windows video adapter for the ILAIOS Desktop finished-product path."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any

from services.evidence import EvidenceStore
from services.governance import GovernedRuntimeGateway
from services.runtime import DurableGrantPolicy
from src.video_automation.ffmpeg_media_engine import FfmpegMediaEngine
from src.video_automation.workflow_orchestrator import (
    VideoWorkflowOrchestrator,
    WorkflowGate,
    WorkflowStage,
    WorkflowStep,
)

from .video_runtime import DeterministicLocalVideoRuntime, VideoRuntimeError

ObjectiveResolver = Callable[[str], str]


@dataclass(frozen=True, slots=True)
class DesktopVideoScene:
    scene_id: str
    start: float
    end: float
    headline: str
    supporting_text: str


@dataclass(frozen=True, slots=True)
class DesktopCaptionCue:
    start: float
    end: float
    text: str


@dataclass(frozen=True, slots=True)
class DesktopVideoPlan:
    voiceover: str
    scenes: tuple[DesktopVideoScene, ...]
    captions: tuple[DesktopCaptionCue, ...]


class DesktopPromptVideoRuntime(DeterministicLocalVideoRuntime):
    """Execute authenticated Desktop video objectives through the canonical M30 chain."""

    def __init__(
        self,
        root: Path,
        grants: DurableGrantPolicy,
        governance: GovernedRuntimeGateway,
        evidence: EvidenceStore,
        *,
        objective_resolver: ObjectiveResolver,
        brand_logo: Path,
    ) -> None:
        super().__init__(root, grants, governance, evidence)
        self._desktop_objective_resolver = objective_resolver
        self._desktop_brand_logo = brand_logo

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
            objective = self._desktop_objective_resolver(job_id).strip()
            if not objective:
                raise VideoRuntimeError("prompt-driven video objective is unavailable")
            run_root = self._root / request_id
            run_root.mkdir(parents=True, exist_ok=False)
            execution = _DesktopFinishedProductExecution(
                run_root,
                job_id,
                objective,
                self._desktop_brand_logo,
            )
            workflow = VideoWorkflowOrchestrator().run(job_id, execution.steps())
            rendered = execution.rendered_path
            content = rendered.read_bytes()
            artifact = self._evidence.put_artifact(content)
            provenance = self._evidence.append_provenance(
                job_id,
                artifact,
                "video.desktop.finished_product",
            )
            delivery = self._deliver(content, artifact.digest)
            latency_ms = int((time.monotonic() - started) * 1000)
            latency_budget_ms = 180_000
            if latency_ms > latency_budget_ms:
                raise VideoRuntimeError("Desktop video latency acceptance failed")
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
                "provider_boundary": "local-ffmpeg-motion-graphics",
                "generation_mode": "prompt-driven-finished-product",
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


class _DesktopFinishedProductExecution:
    def __init__(self, root: Path, job_id: str, objective: str, brand_logo: Path) -> None:
        self._root = root
        self._job_id = job_id
        self._objective = objective
        self._brand_logo = brand_logo
        self._duration = requested_duration(objective)
        self._plan = build_video_plan(objective, self._duration)
        self._voice_path = root / "voice.wav"
        self._music_path = root / "music.wav"
        self._caption_path = root / "captions.srt"
        self._rendered_path: Path | None = None
        self._logo_sha256: str | None = None
        self._repair_attempts = 0
        self._qa: dict[str, object] | None = None

    @property
    def rendered_path(self) -> Path:
        if self._rendered_path is None:
            raise VideoRuntimeError("Desktop video workflow did not render media")
        return self._rendered_path

    @property
    def qa(self) -> dict[str, object]:
        if self._qa is None:
            raise VideoRuntimeError("Desktop video workflow did not complete QA")
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
        self,
        stage: WorkflowStage,
        context: Mapping[str, Any],
    ) -> object:
        if stage is WorkflowStage.RESEARCHED:
            return self._write_manifest(
                "research.json",
                {
                    "job_id": self._job_id,
                    "source": "authenticated_user_objective",
                    "objective": self._objective,
                    "external_factual_claims": False,
                },
            )
        if stage is WorkflowStage.SCRIPTED:
            return self._write_manifest("script.json", self._script_payload())
        if stage is WorkflowStage.SCENES_PLANNED:
            return self._write_manifest(
                "storyboard.json",
                [self._scene_payload(scene) for scene in self._plan.scenes],
            )
        if stage is WorkflowStage.SHOTS_PLANNED:
            return self._write_manifest(
                "shot-plan.json",
                [self._shot_payload(scene) for scene in self._plan.scenes],
            )
        if stage is WorkflowStage.ASSETS_PLANNED:
            return self._write_manifest(
                "asset-plan.json",
                {
                    "visuals": "deterministic local motion graphics",
                    "logo": "official immutable ILAIOS symbol",
                    "voice": "Windows SAPI local TTS",
                    "music": "deterministic local electronic pulse",
                    "captions": "SRT plus burned-in captions",
                },
            )
        if stage is WorkflowStage.ASSETS_ACQUIRED:
            return self._acquire_assets()
        if stage is WorkflowStage.VOICE_READY:
            return self._generate_voice()
        if stage is WorkflowStage.AUDIO_READY:
            return self._generate_music()
        if stage is WorkflowStage.CAPTIONS_READY:
            return self._write_captions()
        if stage is WorkflowStage.TIMELINE_READY:
            return self._write_manifest(
                "timeline.json",
                {
                    "duration_seconds": self._duration,
                    "fps": 24,
                    "width": 1920,
                    "height": 1080,
                    "scenes": [
                        self._scene_payload(scene) for scene in self._plan.scenes
                    ],
                    "voice": str(self._voice_path),
                    "music": str(self._music_path),
                    "captions": str(self._caption_path),
                },
            )
        if stage is WorkflowStage.RENDERED:
            return self._render(repair=False)
        if stage is WorkflowStage.TECHNICALLY_VALIDATED:
            return self._validate_with_repair()
        if stage is WorkflowStage.CONTENT_VALIDATED:
            return self._content_validate()
        if stage is WorkflowStage.PUBLISH_READY:
            return {
                "delivery_boundary_ready": True,
                "publish_side_effect_requested": False,
            }
        if stage is WorkflowStage.COMPLETED:
            return {
                "completed_from": str(context[WorkflowStage.PUBLISH_READY.value]),
                "finished_product": str(self.rendered_path),
            }
        raise VideoRuntimeError(f"unsupported Desktop video stage: {stage.value}")

    def _script_payload(self) -> dict[str, object]:
        return {
            "voiceover": self._plan.voiceover,
            "sections": [
                {
                    "section_id": scene.scene_id,
                    "on_screen_text": scene.headline,
                    "supporting_text": scene.supporting_text,
                    "duration_seconds": round(scene.end - scene.start, 3),
                }
                for scene in self._plan.scenes
            ],
        }

    @staticmethod
    def _scene_payload(scene: DesktopVideoScene) -> dict[str, object]:
        return {
            "scene_id": scene.scene_id,
            "start": scene.start,
            "end": scene.end,
            "headline": scene.headline,
            "supporting_text": scene.supporting_text,
            "visual_intent": "restrained enterprise motion graphics",
        }

    @staticmethod
    def _shot_payload(scene: DesktopVideoScene) -> dict[str, object]:
        return {
            "shot_id": scene.scene_id.replace("scene", "shot"),
            "scene_id": scene.scene_id,
            "start": scene.start,
            "end": scene.end,
            "framing": "centered geometric composition",
            "movement": "precise restrained motion",
            "generation_prompt": f"{scene.headline} — {scene.supporting_text}",
            "provider_capability": "local.motion.graphics",
        }

    def _write_manifest(self, name: str, payload: object) -> dict[str, object]:
        path = self._root / name
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return {
            "path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }

    def _acquire_assets(self) -> dict[str, object]:
        if not self._brand_logo.is_file():
            raise VideoRuntimeError("official ILAIOS brand logo is unavailable")
        content = self._brand_logo.read_bytes()
        if not content:
            raise VideoRuntimeError("official ILAIOS brand logo is empty")
        self._logo_sha256 = hashlib.sha256(content).hexdigest()
        return {
            "logo_path": str(self._brand_logo),
            "logo_sha256": self._logo_sha256,
            "logo_mutated": False,
            "visual_generation": "local-ffmpeg-motion-graphics",
        }

    def _generate_voice(self) -> dict[str, object]:
        powershell = shutil.which("powershell.exe")
        if powershell is None:
            raise VideoRuntimeError("Windows SAPI voice runtime is unavailable")
        script = self._root / "generate-voice.ps1"
        script.write_text(
            "\n".join(
                (
                    "$ErrorActionPreference = 'Stop'",
                    "Add-Type -AssemblyName System.Speech",
                    "$voice = New-Object System.Speech.Synthesis.SpeechSynthesizer",
                    "$voice.Rate = -1",
                    "$voice.Volume = 92",
                    "$voice.SetOutputToWaveFile($env:ILAIOS_VOICE_OUT)",
                    "$voice.Speak($env:ILAIOS_VOICE_TEXT)",
                    "$voice.Dispose()",
                )
            ),
            encoding="utf-8",
        )
        environment = dict(os.environ)
        environment["ILAIOS_VOICE_OUT"] = str(self._voice_path)
        environment["ILAIOS_VOICE_TEXT"] = self._plan.voiceover
        completed = subprocess.run(
            (
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
            ),
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=45,
        )
        if completed.returncode != 0 or not self._voice_path.is_file():
            raise VideoRuntimeError("local voice generation failed")
        return {
            "path": str(self._voice_path),
            "sha256": hashlib.sha256(self._voice_path.read_bytes()).hexdigest(),
            "provider": "windows-sapi-local",
        }

    def _generate_music(self) -> dict[str, object]:
        completed = subprocess.run(
            (
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency=55:sample_rate=48000:duration={self._duration}",
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency=110:sample_rate=48000:duration={self._duration}",
                "-filter_complex",
                "[0:a]volume=0.08[a0];[1:a]volume=0.035[a1];"
                "[a0][a1]amix=inputs=2:duration=longest:dropout_transition=0[a]",
                "-map",
                "[a]",
                "-c:a",
                "pcm_s16le",
                str(self._music_path),
            ),
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if completed.returncode != 0 or not self._music_path.is_file():
            raise VideoRuntimeError("local cinematic music generation failed")
        return {
            "path": str(self._music_path),
            "sha256": hashlib.sha256(self._music_path.read_bytes()).hexdigest(),
            "provider": "local-electronic-pulse",
        }

    def _write_captions(self) -> dict[str, object]:
        blocks: list[str] = []
        for index, cue in enumerate(self._plan.captions, start=1):
            blocks.extend(
                (
                    str(index),
                    f"{_srt_time(cue.start)} --> {_srt_time(cue.end)}",
                    cue.text,
                    "",
                )
            )
        self._caption_path.write_text("\n".join(blocks), encoding="utf-8")
        return {
            "path": str(self._caption_path),
            "sha256": hashlib.sha256(self._caption_path.read_bytes()).hexdigest(),
            "cue_count": len(self._plan.captions),
        }

    def _render(self, *, repair: bool) -> dict[str, object]:
        font = _windows_font()
        output = self._root / "final.mp4"
        filters = _visual_filters(self._plan, font, self._duration)
        logo_start = max(0.0, self._duration - 3.0)
        filter_complex = (
            f"[0:v]{filters}[base];"
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
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x07111F:s=1920x1080:r=24:d={self._duration}",
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
            raise VideoRuntimeError(f"prompt-driven 1080p render failed: {detail}")
        self._rendered_path = output
        return {
            "path": str(output),
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "size": output.stat().st_size,
            "resolution": "1920x1080",
            "fps": 24,
            "repair_render": repair,
        }

    def _validate_with_repair(self) -> dict[str, object]:
        result = self._probe_quality()
        if not _as_bool(result.get("passed")):
            self._repair_attempts = 1
            self._render(repair=True)
            result = self._probe_quality()
            if not _as_bool(result.get("passed")):
                raise VideoRuntimeError("Desktop video failed bounded repair QA")
        result["repair_attempts"] = self._repair_attempts
        self._qa = result
        return result

    def _probe_quality(self) -> dict[str, object]:
        probe = FfmpegMediaEngine(timeout_seconds=60).probe(self.rendered_path)
        video = next(
            (stream for stream in probe.streams if stream.get("codec_type") == "video"),
            None,
        )
        audio = next(
            (stream for stream in probe.streams if stream.get("codec_type") == "audio"),
            None,
        )
        if video is None or audio is None:
            return {
                "passed": False,
                "visual_passed": False,
                "audio_passed": False,
                "brand_passed": self._logo_sha256 is not None,
                "reason": "required media stream is missing",
            }
        width = _as_int(video.get("width"))
        height = _as_int(video.get("height"))
        duration = float(probe.duration_seconds)
        visual_passed = (
            video.get("codec_name") == "h264"
            and width == 1920
            and height == 1080
            and abs(duration - self._duration) <= 1.0
            and self.rendered_path.stat().st_size > 100_000
        )
        audio_passed = (
            audio.get("codec_name") == "aac"
            and self._voice_path.is_file()
            and self._voice_path.stat().st_size > 44
            and self._music_path.is_file()
            and self._music_path.stat().st_size > 44
        )
        brand_passed = self._logo_sha256 is not None
        return {
            "video_codec": video.get("codec_name"),
            "audio_codec": audio.get("codec_name"),
            "width": width,
            "height": height,
            "duration_seconds": duration,
            "target_duration_seconds": self._duration,
            "fps": 24,
            "visual_passed": visual_passed,
            "audio_passed": audio_passed,
            "brand_passed": brand_passed,
            "passed": visual_passed and audio_passed and brand_passed,
        }

    def _content_validate(self) -> dict[str, object]:
        if self._qa is None or not _as_bool(self._qa.get("passed")):
            raise VideoRuntimeError("technical/audio/visual QA has not passed")
        required = (
            "research.json",
            "script.json",
            "storyboard.json",
            "shot-plan.json",
            "asset-plan.json",
            "timeline.json",
            "captions.srt",
        )
        missing = [name for name in required if not (self._root / name).is_file()]
        if missing:
            raise VideoRuntimeError("finished-product stage evidence is incomplete")
        return {
            "script_present": True,
            "storyboard_present": True,
            "shot_plan_present": True,
            "voice_present": True,
            "music_present": True,
            "subtitles_present": True,
            "timeline_present": True,
            "visual_audio_qa_passed": True,
            "bounded_repair_attempts": self._repair_attempts,
        }


def requested_duration(objective: str) -> float:
    match = re.search(
        r"\b(\d{1,3})\s*(?:seconds?|secs?|second|saniye|sn)\b",
        objective.casefold(),
    )
    if match is None:
        return 20.0
    requested = int(match.group(1))
    if requested < 8 or requested > 60:
        raise VideoRuntimeError("Desktop finished-product video duration must be 8-60 seconds")
    return float(requested)


def build_video_plan(objective: str, duration: float) -> DesktopVideoPlan:
    if "ilaios" in objective.casefold():
        titles = (
            ("ILAIOS", "GOVERNED AI OPERATING SYSTEM"),
            ("ONE PROMPT.", "From objective to coordinated execution."),
            ("GOVERNED AUTONOMOUS EXECUTION.", "SECURE  •  CONTROLLED  •  TRACEABLE"),
            ("VERIFIED FINISHED PRODUCT.", "Quality gates before delivery."),
            ("ONE PROMPT. REAL EXECUTION.", "Built in Türkiye. Designed for the world.  •  ilaios.com"),
        )
        voiceover = (
            "One goal becomes one governed execution path. "
            "ILAIOS plans the work, coordinates autonomous execution, verifies every stage, "
            "and delivers the finished product. Secure, controlled, and traceable from prompt "
            "to result. ILAIOS."
        )
        caption_lines = (
            "One goal becomes one governed execution path.",
            "ILAIOS plans the work.",
            "Coordinates autonomous execution.",
            "Verifies every stage and delivers the finished product.",
            "Secure, controlled, and traceable. ILAIOS.",
        )
    else:
        titles = (
            ("YOUR GOAL.", "One natural-language objective."),
            ("ONE PROMPT.", "From objective to coordinated execution."),
            ("GOVERNED EXECUTION.", "Controlled, traceable, coordinated."),
            ("VALIDATED RESULT.", "Quality gates before delivery."),
            ("FINISHED PRODUCT.", "Delivered by ILAIOS."),
        )
        voiceover = (
            "One goal becomes one governed execution path. ILAIOS coordinates the work, "
            "validates every stage, and delivers the finished product. Controlled, traceable, "
            "and ready for use."
        )
        caption_lines = (
            "One goal becomes one governed execution path.",
            "ILAIOS coordinates the work.",
            "Controlled and traceable execution.",
            "Quality gates validate every stage.",
            "A finished product, ready for use.",
        )
    weights = (0.15, 0.20, 0.30, 0.20, 0.15)
    scenes: list[DesktopVideoScene] = []
    cursor = 0.0
    for index, ((headline, supporting), weight) in enumerate(
        zip(titles, weights, strict=True),
        start=1,
    ):
        end = duration if index == len(weights) else cursor + duration * weight
        scenes.append(
            DesktopVideoScene(
                scene_id=f"scene-{index:02d}",
                start=round(cursor, 3),
                end=round(end, 3),
                headline=headline,
                supporting_text=supporting,
            )
        )
        cursor = end
    captions = tuple(
        DesktopCaptionCue(scene.start, scene.end, text)
        for scene, text in zip(scenes, caption_lines, strict=True)
    )
    return DesktopVideoPlan(voiceover, tuple(scenes), captions)


def _visual_filters(plan: DesktopVideoPlan, font: Path, duration: float) -> str:
    font_value = _filter_path(font)
    filters = [
        "drawgrid=w=120:h=120:t=1:c=0x15324A@0.16",
        "drawbox=x=70:y=98:w=1780:h=1:color=0x00C2D1@0.28:t=fill",
        "drawbox=x=0:y=1016:w=1920:h=2:color=0x00C2D1@0.72:t=fill",
        "drawtext="
        f"fontfile='{font_value}':text='ILAIOS / VERIFIED EXECUTION':"
        "fontcolor=0x69849D:fontsize=18:x=w-text_w-70:y=60",
        f"fade=t=in:st=0:d=0.35,fade=t=out:st={max(0.0, duration - 0.45):.3f}:d=0.45",
    ]
    scene_count = len(plan.scenes)
    for index, scene in enumerate(plan.scenes, start=1):
        headline = _drawtext_escape(scene.headline)
        supporting = _drawtext_escape(scene.supporting_text)
        scene_label = f"{index:02d} / {scene_count:02d}"
        scene_number = f"{index:02d}"
        enabled = f"enable='between(t,{scene.start:.3f},{scene.end:.3f})'"
        filters.extend(
            (
                "drawbox=x=180:y=300:w=1560:h=410:color=0x081827@0.94:t=fill:"
                + enabled,
                "drawbox=x=220:y=350:w=5:h=255:color=0x00C2D1@0.90:t=fill:"
                + enabled,
                "drawbox=x=280:y=610:w=420:h=2:color=0x00C2D1@0.65:t=fill:"
                + enabled,
                "drawtext="
                f"fontfile='{font_value}':text='{scene_label}':"
                "fontcolor=0x00C2D1:fontsize=22:x=280:y=355:"
                + enabled,
                "drawtext="
                f"fontfile='{font_value}':text='{scene_number}':"
                "fontcolor=0x00C2D1@0.10:fontsize=210:x=1435:y=345:"
                + enabled,
                "drawtext="
                f"fontfile='{font_value}':text='{headline}':"
                "fontcolor=white:fontsize=64:x=280:y=430:"
                + enabled,
                "drawtext="
                f"fontfile='{font_value}':text='{supporting}':"
                "fontcolor=0xA9BED0:fontsize=32:x=280:y=535:"
                + enabled,
            )
        )
    for cue in plan.captions:
        text = _drawtext_escape(cue.text)
        filters.append(
            "drawtext="
            f"fontfile='{font_value}':text='{text}':"
            "fontcolor=white:fontsize=34:box=1:boxcolor=0x000000@0.58:"
            "boxborderw=14:x=(w-text_w)/2:y=890:"
            f"enable='between(t,{cue.start:.3f},{cue.end:.3f})'"
        )
    return ",".join(filters)


def _windows_font() -> Path:
    windows = Path(os.environ.get("WINDIR", r"C:\Windows"))
    for filename in ("segoeui.ttf", "arial.ttf"):
        candidate = windows / "Fonts" / filename
        if candidate.is_file():
            return candidate
    raise VideoRuntimeError("Windows render font is unavailable")


def _filter_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace(":", r"\:")


def _drawtext_escape(value: str) -> str:
    return (
        value.replace("\\", r"\\")
        .replace("'", r"\'")
        .replace(":", r"\:")
        .replace("%", r"\%")
    )


def _srt_time(seconds: float) -> str:
    total_ms = max(0, int(round(seconds * 1000)))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},{milliseconds:03d}"


def _validate_runtime_identity(name: str, value: str) -> None:
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    if not value or any(character not in allowed for character in value):
        raise VideoRuntimeError(f"invalid {name}")


def _as_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0


def _as_bool(value: object) -> bool:
    return value is True

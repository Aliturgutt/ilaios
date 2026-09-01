from __future__ import annotations

import subprocess
from hashlib import sha256
from pathlib import Path

import pytest

from src.video_automation.episode_assembly_execution import (
    EpisodeAssemblyExecutionCoordinator,
    EpisodeAssemblyExecutionError,
    EpisodeAssemblyExecutorRequest,
    EpisodeAssemblyExecutorResult,
    EpisodeAssemblyInputClip,
    FfmpegEpisodeAssemblyExecutor,
)
from src.video_automation.episode_assembly_request_planning import (
    EpisodeAssemblyOutputPolicy,
    EpisodeAssemblyRequest,
    EpisodeAssemblyRequestClip,
)
from src.video_automation.media_technical_validation import (
    EpisodeMediaTechnicalValidationManifest,
    MediaProbeObservation,
    MediaTechnicalValidationStatus,
    ValidatedMediaAsset,
)


class _Executor:
    def __init__(self, write_output: bool = True, other_path: bool = False) -> None:
        self.write_output = write_output
        self.other_path = other_path
        self.calls: list[EpisodeAssemblyExecutorRequest] = []

    @property
    def executor_id(self) -> str:
        return "fake-executor-v1"

    def execute(
        self, request: EpisodeAssemblyExecutorRequest
    ) -> EpisodeAssemblyExecutorResult:
        self.calls.append(request)
        output = Path(request.output_path)
        if self.write_output:
            output.write_bytes(
                b"|".join(Path(c.local_path).read_bytes() for c in request.clips)
            )
        return EpisodeAssemblyExecutorResult(
            str(output.with_name("other.mp4") if self.other_path else output),
            {"adapter": "fake"},
        )


def _obs() -> MediaProbeObservation:
    return MediaProbeObservation("mp4", 5.0, 1080, 1920, 24.0, "h264", "aac", 1, 1)


def _request(ids: tuple[str, ...] = ("asset-1", "asset-2")) -> EpisodeAssemblyRequest:
    clips = tuple(
        EpisodeAssemblyRequestClip(i, a, f"dispatch-{i}", f"job-{i}", i, 1)
        for i, a in enumerate(ids, 1)
    )
    return EpisodeAssemblyRequest(
        "request-001",
        "plan-001",
        "validation-001",
        "episode-001",
        clips,
        EpisodeAssemblyOutputPolicy("mp4", "h264", "aac", 1080, 1920, 24),
        {"clip_count": str(len(clips))},
    )


def _manifest(
    tmp: Path, ids: tuple[str, ...] = ("asset-1", "asset-2")
) -> EpisodeMediaTechnicalValidationManifest:
    assets = []
    for i, a in enumerate(ids, 1):
        body = f"clip-{i}".encode()
        p = tmp / f"clip-{i}.mp4"
        p.write_bytes(body)
        assets.append(
            ValidatedMediaAsset(
                a,
                "provider",
                str(p),
                sha256(body).hexdigest(),
                len(body),
                "video/mp4",
                MediaTechnicalValidationStatus.PASSED,
                _obs(),
                (),
                f"evidence-{i}",
                {},
            )
        )
    return EpisodeMediaTechnicalValidationManifest(
        "media-validation-001",
        "retrieval-001",
        "result-001",
        "dispatch-001",
        "episode-001",
        tuple(assets),
        len(assets),
        len(assets),
        0,
        MediaTechnicalValidationStatus.PASSED,
        "profile-001",
        "probe-001",
        {},
    )


def test_executes_in_order(tmp_path: Path) -> None:
    ex = _Executor()
    art = EpisodeAssemblyExecutionCoordinator(ex).execute(
        _request(), _manifest(tmp_path), tmp_path / "out"
    )
    assert (
        art.source_asset_ids == ("asset-1", "asset-2")
        and Path(art.output_path).read_bytes() == b"clip-1|clip-2"
    )


def test_deterministic(tmp_path: Path) -> None:
    c = EpisodeAssemblyExecutionCoordinator(_Executor())
    r = _request()
    m = _manifest(tmp_path)
    assert (
        c.execute(r, m, tmp_path / "out").artifact_id
        == c.execute(r, m, tmp_path / "out").artifact_id
    )


def test_episode_mismatch(tmp_path: Path) -> None:
    r = _request()
    object.__setattr__(r, "episode_id", "other")
    with pytest.raises(EpisodeAssemblyExecutionError, match="episode_id"):
        EpisodeAssemblyExecutionCoordinator(_Executor()).execute(
            r, _manifest(tmp_path), tmp_path / "out"
        )


def test_manifest_must_pass(tmp_path: Path) -> None:
    m = _manifest(tmp_path)
    object.__setattr__(m, "status", MediaTechnicalValidationStatus.FAILED)
    with pytest.raises(EpisodeAssemblyExecutionError, match="must pass"):
        EpisodeAssemblyExecutionCoordinator(_Executor()).execute(
            _request(), m, tmp_path / "out"
        )


def test_assets_exact_match(tmp_path: Path) -> None:
    with pytest.raises(EpisodeAssemblyExecutionError, match="exactly match"):
        EpisodeAssemblyExecutionCoordinator(_Executor()).execute(
            _request(("asset-1",)), _manifest(tmp_path), tmp_path / "out"
        )


def test_missing_file(tmp_path: Path) -> None:
    m = _manifest(tmp_path)
    Path(m.assets[0].local_path).unlink()
    with pytest.raises(EpisodeAssemblyExecutionError, match="does not exist"):
        EpisodeAssemblyExecutionCoordinator(_Executor()).execute(
            _request(), m, tmp_path / "out"
        )


def test_size_mismatch(tmp_path: Path) -> None:
    m = _manifest(tmp_path)
    Path(m.assets[0].local_path).write_bytes(b"different-size")
    with pytest.raises(EpisodeAssemblyExecutionError, match="byte length"):
        EpisodeAssemblyExecutionCoordinator(_Executor()).execute(
            _request(), m, tmp_path / "out"
        )


def test_hash_mismatch(tmp_path: Path) -> None:
    m = _manifest(tmp_path)
    Path(m.assets[0].local_path).write_bytes(b"clip-X")
    with pytest.raises(EpisodeAssemblyExecutionError, match="SHA-256"):
        EpisodeAssemblyExecutionCoordinator(_Executor()).execute(
            _request(), m, tmp_path / "out"
        )


def test_executor_path_mismatch(tmp_path: Path) -> None:
    with pytest.raises(EpisodeAssemblyExecutionError, match="output_path"):
        EpisodeAssemblyExecutionCoordinator(_Executor(other_path=True)).execute(
            _request(), _manifest(tmp_path), tmp_path / "out"
        )


def test_missing_output(tmp_path: Path) -> None:
    with pytest.raises(EpisodeAssemblyExecutionError, match="does not exist"):
        EpisodeAssemblyExecutionCoordinator(_Executor(write_output=False)).execute(
            _request(), _manifest(tmp_path), tmp_path / "out"
        )


def test_empty_output(tmp_path: Path) -> None:
    class E(_Executor):
        def execute(
            self, request: EpisodeAssemblyExecutorRequest
        ) -> EpisodeAssemblyExecutorResult:
            Path(request.output_path).write_bytes(b"")
            return EpisodeAssemblyExecutorResult(request.output_path)

    with pytest.raises(EpisodeAssemblyExecutionError, match="must not be empty"):
        EpisodeAssemblyExecutionCoordinator(E()).execute(
            _request(), _manifest(tmp_path), tmp_path / "out"
        )


def test_unsupported_container(tmp_path: Path) -> None:
    r = _request()
    object.__setattr__(
        r,
        "output_policy",
        EpisodeAssemblyOutputPolicy("avi", "h264", "aac", 1080, 1920, 24),
    )
    with pytest.raises(EpisodeAssemblyExecutionError, match="unsupported"):
        EpisodeAssemblyExecutionCoordinator(_Executor()).execute(
            r, _manifest(tmp_path), tmp_path / "out"
        )


def test_artifact_metadata_immutable(tmp_path: Path) -> None:
    a = EpisodeAssemblyExecutionCoordinator(_Executor()).execute(
        _request(), _manifest(tmp_path), tmp_path / "out"
    )
    with pytest.raises(TypeError):
        a.metadata["x"] = "y"  # type: ignore[index]


def _executor_request(tmp: Path) -> EpisodeAssemblyExecutorRequest:
    p = tmp / "clip.mp4"
    p.write_bytes(b"clip")
    return EpisodeAssemblyExecutorRequest(
        "request-1",
        "episode-1",
        (
            EpisodeAssemblyInputClip(
                1, "asset-1", str(p), sha256(b"clip").hexdigest(), 4
            ),
        ),
        str(tmp / "output.mp4"),
        "mp4",
        "h264",
        "aac",
        1080,
        1920,
        24,
    )


def test_ffmpeg_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    r = _executor_request(tmp_path)

    def run(cmd: tuple[str, ...], **kwargs: object) -> subprocess.CompletedProcess[str]:
        Path(r.output_path).write_bytes(b"assembled")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", run)
    assert FfmpegEpisodeAssemblyExecutor().execute(r).output_path == r.output_path
    assert not Path(r.output_path + ".concat.txt").exists()


def test_ffmpeg_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    r = _executor_request(tmp_path)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 1, "", "render failed"),
    )
    with pytest.raises(EpisodeAssemblyExecutionError, match="render failed"):
        FfmpegEpisodeAssemblyExecutor().execute(r)


def test_result_metadata_immutable() -> None:
    r = EpisodeAssemblyExecutorResult("output.mp4", {"a": "b"})
    with pytest.raises(TypeError):
        r.metadata["x"] = "y"  # type: ignore[index]


def test_request_rejects_noncontiguous(tmp_path: Path) -> None:
    with pytest.raises(EpisodeAssemblyExecutionError, match="contiguous"):
        EpisodeAssemblyExecutorRequest(
            "r",
            "e",
            (EpisodeAssemblyInputClip(2, "a", str(tmp_path / "a"), "a" * 64, 1),),
            str(tmp_path / "o.mp4"),
            "mp4",
            "h264",
            "aac",
            1,
            1,
            1,
        )

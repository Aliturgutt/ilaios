from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest

import services.source_media as source_media_module
from services.source_media import SourceMediaError, SourceMediaRecord, SourceMediaStore
from src.video_automation.media_technical_validation import MediaProbeObservation


class _Probe:
    probe_id = "fake-ffprobe-v1"

    def __init__(
        self,
        *,
        container: str = "mov,mp4,m4a,3gp,3g2,mj2",
        duration_seconds: float = 12.0,
        width: int = 1920,
        height: int = 1080,
        frames_per_second: float = 30.0,
        video_codec: str = "h264",
        audio_codec: str | None = "aac",
        video_stream_count: int = 1,
        audio_stream_count: int = 1,
    ) -> None:
        self.observation = MediaProbeObservation(
            container=container,
            duration_seconds=duration_seconds,
            width=width,
            height=height,
            frames_per_second=frames_per_second,
            video_codec=video_codec,
            audio_codec=audio_codec,
            video_stream_count=video_stream_count,
            audio_stream_count=audio_stream_count,
        )
        self.paths: list[Path] = []

    def probe(self, path: Path) -> MediaProbeObservation:
        self.paths.append(path)
        return self.observation


def _mp4(payload: bytes = b"payload") -> bytes:
    return b"\x00\x00\x00\x18ftypisom" + payload


def _store(tmp_path: Path, probe: _Probe | None = None) -> SourceMediaStore:
    return SourceMediaStore(
        tmp_path / "source-media.sqlite3",
        tmp_path / "source-media" / "blobs",
        probe=probe or _Probe(),
    )


def _put(
    store: SourceMediaStore,
    payload: bytes,
    *,
    filename: str,
    principal_id: str = "user-1",
    tenant_id: str = "tenant-1",
) -> SourceMediaRecord:
    return store.put(
        content=_mp4(payload),
        claimed_mime_type="video/mp4",
        original_filename=filename,
        principal_id=principal_id,
        tenant_id=tenant_id,
    )


def test_source_media_is_content_addressed_owned_and_immutably_bound(tmp_path: Path) -> None:
    probe = _Probe()
    store = _store(tmp_path, probe)
    content = _mp4()
    record = store.put(
        content=content,
        claimed_mime_type="video/mp4",
        original_filename="source.mp4",
        principal_id="user-1",
        tenant_id="tenant-1",
    )
    assert record.asset_id.startswith("src-")
    assert record.sha256 == sha256(content).hexdigest()
    assert record.duration_seconds == 12.0
    assert record.width == 1920
    assert record.height == 1080
    assert record.probe_id == "fake-ffprobe-v1"
    assert len(probe.paths) == 1
    assert store.require_registered_path(record.asset_id).read_bytes() == content

    bound = store.bind_request(
        "exec-source-1",
        record.asset_id,
        principal_id="user-1",
        tenant_id="tenant-1",
    )
    assert bound == record
    assert store.for_request("exec-source-1") == record
    assert (
        store.bind_request(
            "exec-source-1",
            record.asset_id,
            principal_id="user-1",
            tenant_id="tenant-1",
        )
        == record
    )

    other = store.put(
        content=_mp4(b"other"),
        claimed_mime_type="video/mp4",
        original_filename="other.mp4",
        principal_id="user-1",
        tenant_id="tenant-1",
    )
    with pytest.raises(SourceMediaError, match="immutable"):
        store.bind_request(
            "exec-source-1",
            other.asset_id,
            principal_id="user-1",
            tenant_id="tenant-1",
        )


def test_cross_tenant_source_media_access_fails_closed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    record = _put(store, b"source", filename="source.mp4")
    with pytest.raises(SourceMediaError, match="ownership mismatch"):
        store.get_owned(
            record.asset_id,
            principal_id="user-1",
            tenant_id="tenant-2",
        )
    with pytest.raises(SourceMediaError, match="ownership mismatch"):
        store.bind_request(
            "exec-cross-tenant",
            record.asset_id,
            principal_id="user-1",
            tenant_id="tenant-2",
        )


def test_source_media_rejects_mime_signature_and_technical_spoofing(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(SourceMediaError, match="video/mp4"):
        store.put(
            content=_mp4(),
            claimed_mime_type="video/quicktime",
            original_filename="source.mp4",
            principal_id="user-1",
            tenant_id="tenant-1",
        )
    with pytest.raises(SourceMediaError, match="ftyp"):
        store.put(
            content=b"not-an-mp4",
            claimed_mime_type="video/mp4",
            original_filename="source.mp4",
            principal_id="user-1",
            tenant_id="tenant-1",
        )

    wrong_container = _store(
        tmp_path / "wrong-container",
        _Probe(container="matroska,webm"),
    )
    with pytest.raises(SourceMediaError, match="container"):
        wrong_container.put(
            content=_mp4(),
            claimed_mime_type="video/mp4",
            original_filename="source.mp4",
            principal_id="user-1",
            tenant_id="tenant-1",
        )

    two_video_streams = _store(tmp_path / "streams", _Probe(video_stream_count=2))
    with pytest.raises(SourceMediaError, match="exactly one video stream"):
        two_video_streams.put(
            content=_mp4(),
            claimed_mime_type="video/mp4",
            original_filename="source.mp4",
            principal_id="user-1",
            tenant_id="tenant-1",
        )


def test_source_media_rejects_unsupported_codec_duration_and_filename(tmp_path: Path) -> None:
    unsupported = _store(tmp_path / "codec", _Probe(video_codec="mpeg2video"))
    with pytest.raises(SourceMediaError, match="codec"):
        unsupported.put(
            content=_mp4(),
            claimed_mime_type="video/mp4",
            original_filename="source.mp4",
            principal_id="user-1",
            tenant_id="tenant-1",
        )

    too_long = _store(tmp_path / "duration", _Probe(duration_seconds=901.0))
    with pytest.raises(SourceMediaError, match="duration"):
        too_long.put(
            content=_mp4(),
            claimed_mime_type="video/mp4",
            original_filename="source.mp4",
            principal_id="user-1",
            tenant_id="tenant-1",
        )

    normal = _store(tmp_path / "filename")
    with pytest.raises(SourceMediaError, match=".mp4"):
        normal.put(
            content=_mp4(),
            claimed_mime_type="video/mp4",
            original_filename="source.mov",
            principal_id="user-1",
            tenant_id="tenant-1",
        )


def test_registered_source_path_detects_post_admission_tampering(tmp_path: Path) -> None:
    store = _store(tmp_path)
    record = _put(store, b"source", filename="source.mp4")
    path = store.require_registered_path(record.asset_id)
    path.write_bytes(_mp4(b"tampered"))
    with pytest.raises(SourceMediaError, match="size changed|integrity"):
        store.require_registered_path(record.asset_id)


def test_unbound_source_uploads_are_bounded_and_discardable(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = _put(store, b"first", filename="first.mp4")
    _put(store, b"second", filename="second.mp4")
    with pytest.raises(SourceMediaError, match="too many unsubmitted"):
        _put(store, b"third", filename="third.mp4")

    assert store.discard_unbound(
        first.asset_id,
        principal_id="user-1",
        tenant_id="tenant-1",
    )
    replacement = _put(store, b"third", filename="third.mp4")
    assert replacement.asset_id.startswith("src-")
    with pytest.raises(SourceMediaError, match="unknown source media"):
        store.get_owned(
            first.asset_id,
            principal_id="user-1",
            tenant_id="tenant-1",
        )


def test_bound_source_cannot_be_discarded_through_upload_boundary(tmp_path: Path) -> None:
    store = _store(tmp_path)
    record = _put(store, b"bound", filename="bound.mp4")
    store.bind_request(
        "exec-bound-source",
        record.asset_id,
        principal_id="user-1",
        tenant_id="tenant-1",
    )
    with pytest.raises(SourceMediaError, match="bound source media"):
        store.discard_unbound(
            record.asset_id,
            principal_id="user-1",
            tenant_id="tenant-1",
        )
    assert store.require_registered_path(record.asset_id).is_file()


def test_unbound_source_byte_quota_is_enforced_before_new_blob(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path)
    first_content = _mp4(b"first")
    monkeypatch.setattr(
        source_media_module,
        "MAX_UNBOUND_SOURCE_MEDIA_BYTES",
        len(first_content) + 1,
    )
    store.put(
        content=first_content,
        claimed_mime_type="video/mp4",
        original_filename="first.mp4",
        principal_id="user-1",
        tenant_id="tenant-1",
    )
    with pytest.raises(SourceMediaError, match="256 MiB safety quota"):
        _put(store, b"second", filename="second.mp4")

import inspect
import json
from pathlib import Path

from services.control_plane import server


def test_ready_file_is_published_only_after_complete_json(
    tmp_path: Path, monkeypatch,
) -> None:
    target = tmp_path / "control-plane-ready.json"
    payload: dict[str, object] = {
        "host": "127.0.0.1",
        "port": 43210,
        "schema_version": 1,
        "knowledge_enabled": False,
    }
    observed_replace = False
    real_replace = server.os.replace

    def observing_replace(source: str | Path, destination: str | Path) -> None:
        nonlocal observed_replace
        observed_replace = True
        source_path = Path(source)
        assert Path(destination) == target
        assert not target.exists()
        assert json.loads(source_path.read_text(encoding="utf-8")) == payload
        real_replace(source, destination)

    monkeypatch.setattr(server.os, "replace", observing_replace)

    server._write_ready_file_atomically(target, payload)

    assert observed_replace
    assert json.loads(target.read_text(encoding="utf-8")) == payload
    assert list(tmp_path.glob(".*.tmp")) == []


def test_control_plane_main_uses_atomic_ready_file_publisher() -> None:
    source = inspect.getsource(server.main)
    assert "_write_ready_file_atomically(arguments.ready_file, ready)" in source
    assert "arguments.ready_file.write_text" not in source

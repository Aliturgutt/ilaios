from __future__ import annotations

import threading

import pytest

from services.desktop_identity_server import DesktopIdentityHTTPServer
from services.source_media_desktop import SourceMediaDesktopIdentityHTTPServer


def _bare_server() -> SourceMediaDesktopIdentityHTTPServer:
    server = object.__new__(SourceMediaDesktopIdentityHTTPServer)
    server._serve_forever_active = threading.Event()
    return server


def test_shutdown_is_noop_after_serve_loop_has_returned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = _bare_server()
    calls: list[str] = []

    def fake_shutdown(_self: DesktopIdentityHTTPServer) -> None:
        calls.append("shutdown")

    monkeypatch.setattr(
        DesktopIdentityHTTPServer,
        "shutdown",
        fake_shutdown,
    )

    server.shutdown()
    assert calls == []

    server._serve_forever_active.set()
    server.shutdown()
    assert calls == ["shutdown"]


def test_serve_loop_marks_only_the_live_shutdown_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = _bare_server()
    active_during_parent: list[bool] = []

    def fake_serve_forever(
        _self: DesktopIdentityHTTPServer,
        *,
        poll_interval: float = 0.5,
    ) -> None:
        del poll_interval
        active_during_parent.append(server._serve_forever_active.is_set())

    monkeypatch.setattr(
        DesktopIdentityHTTPServer,
        "serve_forever",
        fake_serve_forever,
    )

    server.serve_forever()

    assert active_during_parent == [True]
    assert not server._serve_forever_active.is_set()

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "apps" / "desktop" / "sidecar" / "ilaios_control_plane_sidecar.py"
LOCAL_RUNTIME = ROOT / "apps" / "desktop" / "lib" / "control_plane" / "local_runtime.dart"


def test_packaged_desktop_uses_desktop_pid_as_authoritative_sidecar_owner() -> None:
    source = SIDECAR.read_text(encoding="utf-8")

    assert "if arguments.desktop_pid is None" in source
    assert "parent_watchdog.start()" in source
    assert "if parent_watchdog is not None:" in source
    assert "desktop_watchdog.start()" in source

    conditional = source.index("if arguments.desktop_pid is None")
    parent_start = source.index("if parent_watchdog is not None:")
    desktop_start = source.index("desktop_watchdog.start()")
    assert conditional < parent_start < desktop_start


def test_bundled_windows_runtime_passes_owner_pid_and_is_shell_independent() -> None:
    source = LOCAL_RUNTIME.read_text(encoding="utf-8")

    assert "'--desktop-pid'," in source
    assert "'$pid'," in source
    assert "mode: ProcessStartMode.detachedWithStdio" in source
    assert "identityUri.resolve('/v1/runtime/shutdown')" in source


def test_parent_pipe_eof_is_only_a_legacy_fallback_without_desktop_owner() -> None:
    source = SIDECAR.read_text(encoding="utf-8")

    owner_guard = """    parent_watchdog = (
        threading.Thread(
            target=stop_identity_if_parent_pipe_closes,
            name="ilaios-desktop-parent-watchdog",
            daemon=True,
        )
        if arguments.desktop_pid is None
        else None
    )
"""
    assert owner_guard in source

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "apps" / "desktop" / "tool" / "verify_windows_real_acceptance.ps1"


def test_real_windows_acceptance_uses_canonical_full_build_and_sidecar_smoke() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "build_and_run_windows_full.ps1" in source
    assert "smoke_control_plane_sidecar.ps1" in source
    assert "ilaios_desktop.exe" in source
    assert "ilaios_control_plane.exe" in source
    assert "git -C $repoRoot rev-parse HEAD" in source


def test_real_windows_acceptance_cannot_claim_ready_before_human_evidence() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    required_pending = (
        "google_login_real_user",
        "system_online_visible",
        "canonical_agents_visible",
        "pixel_agents_visible_and_stateful",
        "real_factory_action_end_to_end",
        "restart_session_runtime",
        "screenshot_or_video_evidence",
    )
    for field in required_pending:
        assert field in source

    assert "overall_desktop_ready = 'BLOCKED'" in source
    assert "ILAIOS_DESKTOP_REAL_USER_ACCEPTANCE=PENDING" in source
    assert "ILAIOS_DESKTOP_READY=BLOCKED" in source
    assert "ILAIOS_DESKTOP_READY=PASS" not in source

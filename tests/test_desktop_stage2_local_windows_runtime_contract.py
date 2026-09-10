import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_home_local_attachment_pickers_do_not_require_sign_in() -> None:
    home = (
        ROOT
        / "apps/desktop/lib/features/dashboard/reference_home_dashboard_v3.dart"
    ).read_text(encoding="utf-8")

    assert "enabled: !_submitting" in home
    assert "widget.userSession != null && !_submitting" not in home
    assert "Icons.attach_file_rounded" not in home
    assert "key: const Key('home-prompt-attachments')" in home


def test_exact_sha_archive_can_build_the_control_plane_sidecar() -> None:
    builder = (
        ROOT / "apps/desktop/tool/build_control_plane_sidecar.ps1"
    ).read_text(encoding="utf-8")

    assert "git -C $repoRoot rev-parse HEAD" in builder
    assert "^ilaios-([0-9a-fA-F]{40})$" in builder
    assert "Use a git checkout or an exact-SHA GitHub archive" in builder
    assert "ILAIOS_DESKTOP_SOURCE_HEAD=$sourceHead" in builder


def test_full_local_windows_entrypoint_builds_app_and_sidecar() -> None:
    script = (
        ROOT / "apps/desktop/tool/build_and_run_windows_full.ps1"
    ).read_text(encoding="utf-8")

    assert "flutter build windows --release" in script
    assert "build_control_plane_sidecar.ps1" in script
    assert "ilaios_desktop.exe" in script
    assert "ilaios_control_plane.exe" in script
    assert "ILAIOS_DESKTOP_FULL_LOCAL_BUILD=PASS" in script


def test_full_local_sidecar_packages_the_canonical_google_provider() -> None:
    provider_path = (
        ROOT
        / "apps/desktop/packaging/identity/oidc-providers.public.json"
    )
    providers = json.loads(provider_path.read_text(encoding="utf-8"))
    assert len(providers) == 1
    google = providers[0]
    assert google["provider_id"] == "google"
    assert google["display_name"] == "Google"
    assert google["issuer"] == "https://accounts.google.com"
    assert google["authorization_endpoint"].startswith("https://accounts.google.com/")
    assert google["client_id"].endswith(".apps.googleusercontent.com")
    assert google["scopes"] == ["openid", "profile", "email"]
    assert "client_secret" not in google

    builder = (
        ROOT / "apps/desktop/tool/build_control_plane_sidecar.ps1"
    ).read_text(encoding="utf-8")
    assert "oidc-providers.public.json" in builder
    assert '--add-data "$identityProviders;desktop-identity"' in builder

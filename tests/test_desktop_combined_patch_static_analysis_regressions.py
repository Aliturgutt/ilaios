from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
PATCH_SCRIPT = ROOT / "tools" / "desktop" / "apply_combined_typography_reference_patch.py"
EVIDENCE_COLLECTOR = ROOT / "tools" / "desktop" / "collect_v4_screenshot_evidence.ps1"
PATCH_INPUTS = (
    "apps/desktop/lib/features/dashboard/reference_desktop_shell_v11.dart",
    "apps/desktop/lib/features/deliveries/deliveries_view.dart",
    "apps/desktop/lib/features/create/reference_asset_picker.dart",
)


def _generate_patch_output(tmp_path: Path) -> Path:
    for relative in PATCH_INPUTS:
        source = ROOT / relative
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "desktop-regression@ilaios.invalid"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "ILAIOS Desktop Regression"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(["git", "add", "apps/desktop"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "fixture"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [sys.executable, str(PATCH_SCRIPT), str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return tmp_path


def test_combined_7_page_validator_does_not_mutate_fixture_source(tmp_path: Path) -> None:
    output = _generate_patch_output(tmp_path)
    result = subprocess.run(
        ["git", "status", "--porcelain", "--", "apps/desktop"],
        cwd=output,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout == ""


def test_7_page_home_reference_controls_are_direct_and_bounded(tmp_path: Path) -> None:
    output = _generate_patch_output(tmp_path)
    picker = (
        output / "apps/desktop/lib/features/create/reference_asset_picker.dart"
    ).read_text(encoding="utf-8")

    assert "key: const Key('home-add-document')" in picker
    assert "key: const Key('home-add-image')" in picker
    assert "key: const Key('home-add-video')" in picker
    assert "content: SizedBox(width: 620, child: body)" in picker
    assert "key: const Key('home-canonical-factory-grid')" in picker


def test_7_page_typography_stays_scoped_without_global_shell_zoom(tmp_path: Path) -> None:
    output = _generate_patch_output(tmp_path)
    shell = (
        output
        / "apps/desktop/lib/features/dashboard/reference_desktop_shell_v11.dart"
    ).read_text(encoding="utf-8")
    deliveries = (
        output / "apps/desktop/lib/features/deliveries/deliveries_view.dart"
    ).read_text(encoding="utf-8")

    assert "TextScaler.linear(desktopTextScale)" not in shell
    assert "TextScaler.linear(.95)" not in shell
    assert "DesktopSection.goals," not in shell
    assert "DesktopSection.live," not in shell
    assert "DesktopSection.costs," not in shell
    assert "key: const Key('reference-responsive-viewport-v11')" in shell
    assert "key: const Key('reference-outputs-page')" in deliveries


def test_7_page_png_dimension_decoder_widens_bytes_before_big_endian_shift() -> None:
    collector = EVIDENCE_COLLECTOR.read_text(encoding="utf-8")
    assert "([uint32]$bytes[16] -shl 24)" in collector
    assert "([uint32]$bytes[18] -shl 8)" in collector
    assert "([uint32]$bytes[20] -shl 24)" in collector
    assert "([uint32]$bytes[22] -shl 8)" in collector

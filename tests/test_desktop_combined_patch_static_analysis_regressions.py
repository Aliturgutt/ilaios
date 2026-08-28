from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
PATCH_SCRIPT = ROOT / "tools" / "desktop" / "apply_combined_typography_reference_patch.py"
PATCH_INPUTS = (
    "apps/desktop/lib/features/dashboard/reference_desktop_shell_v10.dart",
    "apps/desktop/lib/features/deliveries/deliveries_view.dart",
    "apps/desktop/lib/app/desktop_app.dart",
    "apps/desktop/lib/features/create/create_view.dart",
    "apps/desktop/lib/features/create/reference_asset_picker_core.dart",
    "apps/desktop/lib/identity/identity_client.dart",
)


def _generate_patch_output(tmp_path: Path) -> Path:
    for relative in PATCH_INPUTS:
        source = ROOT / relative
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    subprocess.run(
        [sys.executable, str(PATCH_SCRIPT), str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return tmp_path


def test_generated_desktop_app_does_not_shadow_reference_count_helper(
    tmp_path: Path,
) -> None:
    output = _generate_patch_output(tmp_path)
    desktop_app = (output / "apps/desktop/lib/app/desktop_app.dart").read_text(
        encoding="utf-8"
    )

    assert "final referenceTargetCount = referenceFactoryCount(objective);" in desktop_app
    assert "hasReferences && referenceTargetCount == 0" in desktop_app
    assert "hasReferences && referenceTargetCount != 1" in desktop_app
    assert "final referenceFactoryCount = referenceFactoryCount(objective);" not in desktop_app


def test_generated_reference_attach_callbacks_use_lint_safe_blocks(
    tmp_path: Path,
) -> None:
    output = _generate_patch_output(tmp_path)
    create_view = (output / "apps/desktop/lib/features/create/create_view.dart").read_text(
        encoding="utf-8"
    )

    assert "if (scope.target != target) {\n                  scope.onTargetChanged(target);" in create_view
    assert "if (!scope.open) {\n                  scope.onToggle();" in create_view
    assert "if (scope.target != target) scope.onTargetChanged(target);" not in create_view
    assert "if (!scope.open) scope.onToggle();" not in create_view

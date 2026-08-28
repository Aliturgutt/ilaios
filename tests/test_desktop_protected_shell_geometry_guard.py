from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "tools" / "desktop" / "check_protected_shell_geometry.py"


def _run_guard(tmp_path: Path, baseline: str, candidate: str) -> subprocess.CompletedProcess[str]:
    baseline_path = tmp_path / "baseline.dart"
    candidate_path = tmp_path / "candidate.dart"
    baseline_path.write_text(baseline, encoding="utf-8")
    candidate_path.write_text(candidate, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(GUARD), str(baseline_path), str(candidate_path)],
        capture_output=True,
        check=False,
        text=True,
    )


def test_formatting_only_normalization_does_not_fail_geometry_guard(tmp_path: Path) -> None:
    formatted_baseline = "const Text('Ready', style: TextStyle(fontSize: 10));\n"
    formatted_candidate = "const Text('Ready', style: TextStyle(fontSize: 11));\n"

    result = _run_guard(tmp_path, formatted_baseline, formatted_candidate)

    assert result.returncode == 0, result.stdout + result.stderr


def test_real_protected_geometry_change_fails_guard(tmp_path: Path) -> None:
    baseline = "const SizedBox(width: 120, height: 40);\n"
    candidate = "const SizedBox(width: 128, height: 40);\n"

    result = _run_guard(tmp_path, baseline, candidate)

    assert result.returncode == 1
    assert "Protected shell geometry changed" in result.stdout
    assert "width: 128" in result.stdout

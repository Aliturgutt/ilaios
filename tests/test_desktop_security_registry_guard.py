from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SECURITY_SKILLS = ROOT / "tools" / "security-factory" / "skills"
SIDECAR_BUILD = ROOT / "apps" / "desktop" / "tool" / "build_control_plane_sidecar.ps1"


def test_desktop_sidecar_guard_matches_canonical_security_methodology_registry() -> None:
    skill_files = sorted(SECURITY_SKILLS.rglob("SKILL.md"))
    names = {path.parent.name for path in skill_files}

    assert names == {
        "auth-authorization-testing",
        "ilaios-agentic-action-audit",
        "ilaios-differential-review",
        "ilaios-security-review",
        "ilaios-supply-chain-audit",
        "ilaios-threat-model",
    }

    script = SIDECAR_BUILD.read_text(encoding="utf-8")
    assert "if ($securitySkillFiles.Count -ne 6)" in script
    assert "if ($securitySkillFiles.Count -ne 5)" not in script

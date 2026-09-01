from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_desktop_sidecar_packages_web_and_browser_skill_roots() -> None:
    script = (
        ROOT / "apps" / "desktop" / "tool" / "build_control_plane_sidecar.ps1"
    ).read_text(encoding="utf-8")
    assert "$webFactorySkills = Join-Path $repoRoot 'tools\\web-factory\\skills'" in script
    assert "$webBrowserSkills = Join-Path $repoRoot 'tools\\web-factory\\browser-skills'" in script
    assert '--add-data "$webFactorySkills;tools/web-factory/skills"' in script
    assert '--add-data "$webBrowserSkills;tools/web-factory/browser-skills"' in script
    assert "import services.web_agent_runtime" in script
    assert "import services.browser_runtime_composition" in script


def test_desktop_sidecar_projects_web_runtime_without_faking_browser_readiness() -> None:
    source = (
        ROOT / "apps" / "desktop" / "sidecar" / "ilaios_control_plane_sidecar.py"
    ).read_text(encoding="utf-8")
    assert "compose_web_agent_runtime(" in source
    assert '"web_agent_target_count": web_agents.target_agent_count' in source
    assert '"web_agent_ai_runtime_configured": web_agents.ai_configured' in source
    assert '"web_agent_browser_tool_required": web_agents.browser_tool_required' in source
    assert '"web_agent_browser_runtime_configured": False' in source
    assert '"web_agent_browser_runtime_configured": True' not in source

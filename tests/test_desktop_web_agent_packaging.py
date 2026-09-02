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


def test_desktop_sidecar_composes_company_knowledge_without_new_authority() -> None:
    source = (
        ROOT / "apps" / "desktop" / "sidecar" / "ilaios_control_plane_sidecar.py"
    ).read_text(encoding="utf-8")
    assert "TenantCompanyKnowledgeRegistry(root / \"company-knowledge\")" in source
    assert "CompanyKnowledgeDesktopIdentityHTTPServer(" in source
    assert "company_knowledge=company_knowledge" in source
    assert '"company_knowledge_upload_configured": True' in source
    assert "SourceMediaDesktopIdentityHTTPServer(" not in source


def test_desktop_sidecar_packages_company_knowledge_parser_dependencies() -> None:
    script = (
        ROOT / "apps" / "desktop" / "tool" / "build_control_plane_sidecar.ps1"
    ).read_text(encoding="utf-8")
    assert "'pypdf==6.16.2'" in script
    assert "import services.company_knowledge_ingestion" in script
    assert "import services.company_knowledge_desktop" in script

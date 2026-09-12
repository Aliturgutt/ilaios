from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps" / "website" / "app"

HOME = APP / "HomePage.tsx"
FACTORIES = APP / "FactoriesPage.tsx"
CAPABILITIES = APP / "CapabilitiesPage.tsx"
USE_ILAIOS = APP / "UseILAIOSPage.tsx"
ARCHITECTURE = APP / "SystemArchitectureMap.tsx"

FACTORY_ROUTES = [
    "/factories/web",
    "/factories/video",
    "/factories/software",
    "/factories/app",
    "/factories/research-data",
    "/factories/security",
    "/factories/creative-document",
    "/factories/commerce-growth",
    "/factories/personal-operations",
]


def test_public_product_surfaces_show_all_nine_factory_routes() -> None:
    for path in (HOME, FACTORIES, CAPABILITIES, USE_ILAIOS):
        source = path.read_text(encoding="utf-8")
        for route in FACTORY_ROUTES:
            assert route in source, f"{path.name} is missing {route}"


def test_home_and_factories_call_out_nine_production_areas() -> None:
    home = HOME.read_text(encoding="utf-8")
    factories = FACTORIES.read_text(encoding="utf-8")

    assert 'outcomesEyebrow: "Nine production areas"' in home
    assert 'outcomesEyebrow: "Dokuz üretim alanı"' in home
    assert 'eyebrow: "Nine production areas"' in factories
    assert 'eyebrow: "Dokuz üretim alanı"' in factories


def test_architecture_surface_covers_all_24_system_areas() -> None:
    source = ARCHITECTURE.read_text(encoding="utf-8")

    for number in range(1, 25):
        assert f'number: "{number:02d}"' in source

    required_topics = [
        "Client surfaces",
        "Identity → tenant → project lifecycle",
        "Authorized context",
        "Goal & acceptance",
        "Planner & orchestration",
        "Capability registry",
        "Policy gateway & governance",
        "Human approval",
        "Execution grant",
        "Nine production areas",
        "Execution layer",
        "State machine",
        "File & document lifecycle",
        "Deployment & environments",
        "Automation & scheduler",
        "Provider governance",
        "API & webhook integrations",
        "Payment & subscription lifecycle",
        "Notifications & communications",
        "Evidence & audit",
        "Data & infrastructure",
        "Admin & support plane",
        "Feedback → improvement loop",
        "External ecosystem",
    ]
    for topic in required_topics:
        assert topic in source


def test_architecture_keeps_factory_count_and_shared_knowledge_boundary_clear() -> None:
    source = ARCHITECTURE.read_text(encoding="utf-8")

    assert "Nine production areas" in source
    assert "Dokuz üretim alanı" in source
    assert "Governed knowledge / RAG" in source
    assert "Knowledge / RAG" not in source.split('title: "Nine production areas"', 1)[1].split("title:", 1)[0]

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps" / "website" / "app"

HOME = APP / "HomePage.tsx"
FACTORIES = APP / "FactoriesPage.tsx"
ARCHITECTURE = APP / "ArchitecturePage.tsx"
ARCHITECTURE_MAP = APP / "SystemArchitectureMap.tsx"

FACTORY_ROUTES = (
    "/factories/web",
    "/factories/video",
    "/factories/software",
    "/factories/app",
    "/factories/research-data",
    "/factories/security",
    "/factories/creative-document",
    "/factories/commerce-growth",
    "/factories/personal-operations",
)


def test_homepage_and_factories_surface_all_nine_factory_routes_in_both_locales() -> None:
    home = HOME.read_text(encoding="utf-8")
    factories = FACTORIES.read_text(encoding="utf-8")

    for route in FACTORY_ROUTES:
        assert f'"{route}"' in home
        assert f'"/tr{route}"' in home
        assert f'"{route}"' in factories
        assert f'"/tr{route}"' in factories

    assert 'outcomesEyebrow: "Nine production areas"' in home
    assert 'outcomesEyebrow: "Dokuz üretim alanı"' in home
    assert 'eyebrow: "Nine production areas"' in factories
    assert 'eyebrow: "Dokuz üretim alanı"' in factories


def test_architecture_page_renders_complete_public_system_map() -> None:
    page = ARCHITECTURE.read_text(encoding="utf-8")
    architecture_map = ARCHITECTURE_MAP.read_text(encoding="utf-8")

    assert 'import SystemArchitectureMap from "./SystemArchitectureMap"' in page
    assert "<SystemArchitectureMap locale={locale} />" in page
    assert 'data-visual-role="system-architecture-map"' in architecture_map

    for number in range(1, 25):
        assert f'[{number}, ' in architecture_map


def test_knowledge_is_described_as_shared_context_not_tenth_factory() -> None:
    architecture_map = ARCHITECTURE_MAP.read_text(encoding="utf-8")

    assert "Knowledge/RAG is shared context, not a tenth factory." in architecture_map
    assert "Knowledge/RAG ortak bağlamdır; onuncu fabrika değildir." in architecture_map

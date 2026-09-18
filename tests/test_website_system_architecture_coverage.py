from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps" / "website" / "app"

HOME = APP / "HomePage.tsx"
FACTORIES = APP / "FactoriesPage.tsx"
CAPABILITIES = APP / "CapabilitiesPage.tsx"
USE_ILAIOS = APP / "UseILAIOSPage.tsx"
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

CANONICAL_FACTORY_LABELS_EN = (
    "Web",
    "Video / Media",
    "Software",
    "App",
    "Research / Data",
    "Security",
    "Creative / Document",
    "Commerce / Growth",
    "Personal Operations",
)

CANONICAL_FACTORY_LABELS_TR = (
    "Web",
    "Video / Medya",
    "Yazılım",
    "Uygulama",
    "Araştırma / Veri",
    "Güvenlik",
    "Creative / Doküman",
    "Commerce / Büyüme",
    "Kişisel Operasyon",
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


def test_public_factory_taxonomy_is_consistent_across_capabilities_and_use_pages() -> None:
    capabilities = CAPABILITIES.read_text(encoding="utf-8")
    use_ilaios = USE_ILAIOS.read_text(encoding="utf-8")

    for label in CANONICAL_FACTORY_LABELS_EN:
        assert f'"{label}"' in capabilities
        assert f'name: "{label}"' in use_ilaios

    for label in CANONICAL_FACTORY_LABELS_TR:
        assert f'"{label}"' in capabilities
        assert f'name: "{label}"' in use_ilaios


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

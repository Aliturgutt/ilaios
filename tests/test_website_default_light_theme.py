from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAYOUT = ROOT / "apps" / "website" / "app" / "layout.tsx"
TOGGLE = ROOT / "apps" / "website" / "app" / "ThemeToggle.tsx"
CHROME = ROOT / "apps" / "website" / "app" / "SiteChrome.tsx"
THEME = ROOT / "apps" / "website" / "app" / "site-v2-finalization.css"
INTERACTION = ROOT / "apps" / "website" / "app" / "final-interaction-redteam.css"
DIAGRAM = ROOT / "apps" / "website" / "app" / "ThemedDiagram.tsx"


def test_website_defaults_to_light_without_overriding_explicit_choice() -> None:
    layout = LAYOUT.read_text(encoding="utf-8")
    toggle = TOGGLE.read_text(encoding="utf-8")

    assert 'const theme = stored === "light" || stored === "dark" ? stored : "light";' in layout
    assert 'document.documentElement.dataset.theme = "light"' in layout
    assert 'document.documentElement.style.colorScheme = "light"' in layout
    assert 'localStorage.setItem(STORAGE_KEY, next)' in toggle


def test_website_default_theme_does_not_follow_system_dark_mode() -> None:
    layout = LAYOUT.read_text(encoding="utf-8")

    assert "prefers-color-scheme" not in layout


def test_shared_header_uses_canonical_theme_specific_horizontal_logos() -> None:
    chrome = CHROME.read_text(encoding="utf-8")

    assert 'className="brand-logo brand-logo-dark"' in chrome
    assert 'src="/brand/logo-horizontal-dark.jpg"' in chrome
    assert 'className="brand-logo brand-logo-light"' in chrome
    assert 'src="/brand/logo-horizontal-light.jpg"' in chrome


def test_light_header_is_canonical_light_surface() -> None:
    theme = THEME.read_text(encoding="utf-8")

    assert 'html[data-theme="light"] .site-header {' in theme
    assert "background: #FFFFFF;" in theme
    assert "border-bottom-color: rgba(10, 10, 10, .10);" in theme
    assert 'html[data-theme="light"] .brand-logo-dark { display: none; }' in theme
    assert 'html[data-theme="light"] .brand-logo-light { display: block; }' in theme


def test_mobile_light_theme_neutralizes_legacy_dark_surfaces() -> None:
    interaction = INTERACTION.read_text(encoding="utf-8")

    for selector in (
        'html[data-theme="light"] body',
        'html[data-theme="light"] .site-header',
        'html[data-theme="light"] .site-footer',
        'html[data-theme="light"] .nav-panel',
        'html[data-theme="light"] .card',
        'html[data-theme="light"] .product-experience',
        'html[data-theme="light"] .contact-directory article',
        'html[data-theme="light"] .canonical-detail-panel',
        'html[data-theme="light"] .themed-diagram',
    ):
        assert selector in interaction

    assert 'html[data-theme="light"] .menu-toggle {' in interaction
    assert "background: #FFFFFF !important;" in interaction
    assert "color: #0A0A0A !important;" in interaction


def test_light_interactions_never_use_white_text_on_light_surfaces() -> None:
    interaction = INTERACTION.read_text(encoding="utf-8")

    assert 'html[data-theme="light"] :where(.button.secondary,.text-link,.contact-directory article > a)' in interaction
    assert "border-color: #2A2A2A !important;" in interaction
    assert "-webkit-text-fill-color: #0A0A0A !important;" in interaction


def test_light_normal_text_uses_high_contrast_neutral_gray() -> None:
    interaction = INTERACTION.read_text(encoding="utf-8")

    assert ".contact-directory article p" in interaction
    assert ".status-note p" in interaction
    assert ".product-stage-control p" in interaction
    assert "color: #2A2A2A !important;" in interaction


def test_light_primary_cta_and_dark_preview_text_are_visible() -> None:
    interaction = INTERACTION.read_text(encoding="utf-8")

    assert 'html[data-theme="light"] .button:not(.secondary)' in interaction
    assert "background: #0A0A0A !important;" in interaction
    assert "-webkit-text-fill-color: #FFFFFF !important;" in interaction
    assert 'html[data-theme="light"] .result-preview {' in interaction
    assert 'html[data-theme="light"] .result-preview :where(span,strong)' in interaction


def test_dark_footer_has_no_blue_ui_text_authority() -> None:
    interaction = INTERACTION.read_text(encoding="utf-8")

    assert 'html[data-theme="dark"] .site-footer {' in interaction
    assert 'html[data-theme="dark"] .site-footer :where(a,p,span,small)' in interaction
    assert "color: #B3B3B3 !important;" in interaction
    assert 'html[data-theme="dark"] .site-footer a:hover' in interaction
    assert "color: #E6E6E6 !important;" in interaction


def test_final_light_theme_authority_loads_after_legacy_theme_layers() -> None:
    layout = LAYOUT.read_text(encoding="utf-8")

    assert layout.index('import "./site-v2-finalization.css";') < layout.index('import "./final-interaction-redteam.css";')


def test_light_factory_explorer_keeps_normal_text_legible() -> None:
    interaction = INTERACTION.read_text(encoding="utf-8")

    assert 'html[data-theme="light"] .factory-index button' in interaction
    assert 'html[data-theme="light"] .factory-detail p' in interaction
    assert "color: #2A2A2A !important;" in interaction


def test_themed_diagram_uses_the_existing_canonical_sprite_assets() -> None:
    diagram = DIAGRAM.read_text(encoding="utf-8")

    assert 'background-image: url("/visuals/ilaios-diagrams.avif")' in THEME.read_text(encoding="utf-8")
    assert "const WIDE_ROWS" in diagram
    assert "src={dark}" not in diagram
    assert "src={light}" not in diagram
    assert "diagram-sprite-dark" in diagram
    assert "diagram-sprite-light" in diagram

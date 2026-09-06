from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAYOUT = ROOT / "apps" / "website" / "app" / "layout.tsx"
TOGGLE = ROOT / "apps" / "website" / "app" / "ThemeToggle.tsx"
CHROME = ROOT / "apps" / "website" / "app" / "SiteChrome.tsx"
THEME = ROOT / "apps" / "website" / "app" / "site-v2-finalization.css"
INTERACTION = ROOT / "apps" / "website" / "app" / "final-interaction-redteam.css"
PALETTE = ROOT / "apps" / "website" / "app" / "brand-palette.css"
DIAGRAM = ROOT / "apps" / "website" / "app" / "ThemedDiagram.tsx"
VISUAL_QA = ROOT / "apps" / "website" / "scripts" / "website-v2-visual-qa.py"


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


def test_dark_header_matches_canonical_logo_field_without_asset_mutation() -> None:
    palette = PALETTE.read_text(encoding="utf-8")
    chrome = CHROME.read_text(encoding="utf-8")

    assert 'className="site-header"' in chrome
    assert 'className="brand"' in chrome
    assert 'html[data-theme="dark"] body .site-header' in palette
    assert 'html[data-theme="dark"] body .site-header .brand' in palette
    assert "background: #07080A !important;" in palette


def test_dark_surface_typography_is_explicitly_light_neutral() -> None:
    interaction = INTERACTION.read_text(encoding="utf-8")

    assert '.capability-matrix-row' in interaction
    assert '.trust-gate > div' in interaction
    assert '.plane-box' in interaction
    assert ':where(h1,h2,h3,h4,strong,b)' in interaction
    assert "color: #FFFFFF !important;" in interaction
    assert ':where(p,small,span,li,i)' in interaction
    assert "color: #B3B3B3 !important;" in interaction


def test_product_experience_helper_text_is_neutral_in_both_themes() -> None:
    interaction = INTERACTION.read_text(encoding="utf-8")

    assert 'html[data-theme="dark"] .product-experience :where(.micro-label,.text-link,.evidence-preview,.evidence-preview span,.evidence-preview li,.product-stage-control p,.product-stage-tabs button,.product-mode-tabs button)' in interaction
    assert 'html[data-theme="light"] .product-experience :where(.evidence-preview,.evidence-preview span,.evidence-preview li,.product-stage-control p,.product-stage-tabs button,.micro-label)' in interaction
    assert "-webkit-text-fill-color: #B3B3B3 !important;" in interaction
    assert "-webkit-text-fill-color: #2A2A2A !important;" in interaction


def test_light_embedded_surfaces_do_not_inherit_dark_on_dark_text() -> None:
    interaction = INTERACTION.read_text(encoding="utf-8")

    assert 'html[data-theme="light"] :where(.detail-directory > a,.runtime-line > div,.capability-matrix-row,.factory-link-cloud a,.security-process article,.principle-directory article,.trust-gate > div,.plane-box,.system-visual-control,.spatial-stage)' in interaction
    assert "background: #FFFFFF !important;" in interaction
    assert "color: #0A0A0A !important;" in interaction
    assert "color: #2A2A2A !important;" in interaction


def test_final_render_authority_contains_no_cyan_or_blue_hex_values() -> None:
    interaction = INTERACTION.read_text(encoding="utf-8").upper()

    assert "#00C2D1" not in interaction
    assert "#146BFF" not in interaction


def test_light_footer_hover_and_focus_keep_dark_text_on_white() -> None:
    palette = PALETTE.read_text(encoding="utf-8")

    assert 'html[data-theme="light"] body .site-footer a:hover' in palette
    assert 'html[data-theme="light"] body .site-footer a:focus-visible' in palette
    assert "-webkit-text-fill-color: var(--brand-carbon) !important;" in palette


def test_mobile_header_keeps_navigation_and_uses_compact_right_anchored_panel() -> None:
    chrome = CHROME.read_text(encoding="utf-8")
    interaction = INTERACTION.read_text(encoding="utf-8")

    assert 'className="site-header"' in chrome
    assert 'className="menu-toggle"' in chrome
    assert 'className={`nav-panel ${open ? "is-open" : ""}`}' in chrome
    assert "ThemeToggle" in chrome
    assert 'className="language-switch"' in chrome
    assert 'className="explore-menu"' in chrome
    assert "left: auto !important;" in interaction
    assert "right: 16px !important;" in interaction
    assert "width: min(320px, calc(100vw - 32px)) !important;" in interaction
    assert ".site-header .nav-panel.is-open" in interaction
    assert "grid-template-columns: 1fr !important;" in interaction


def test_canonical_architecture_flow_is_neutral_grayscale() -> None:
    palette = PALETTE.read_text(encoding="utf-8")

    assert ".canonical-linear" in palette
    assert ".canonical-linear > div" in palette
    assert "background: #141414 !important;" in palette
    assert "border-color: #2A2A2A !important;" in palette
    assert ".canonical-linear > div > span" in palette
    assert "color: #B3B3B3 !important;" in palette


def test_professional_visual_system_uses_shared_rhythm_and_component_geometry() -> None:
    palette = PALETTE.read_text(encoding="utf-8")

    for token in (
        "--ui-section-y: 72px;",
        "--ui-card-pad: 24px;",
        "--ui-control-h: 46px;",
        "--ui-radius: 8px;",
        "--ui-copy-max: 68ch;",
    ):
        assert token in palette
    assert "html body :where(.page-hero,.compact-page-hero)" in palette
    assert "html body :where(.card,.detail-link-card,.flow-card,.plane-card,.journey-card,.output-card" in palette
    assert "html body .site-footer .footer-nav-grid" in palette
    assert "grid-template-columns: repeat(5, minmax(0, 1fr)) !important;" in palette


def test_interaction_polish_never_moves_components_on_hover_or_focus() -> None:
    palette = PALETTE.read_text(encoding="utf-8")

    assert "transition: background-color 120ms ease, color 120ms ease, border-color 120ms ease !important;" in palette
    assert "transform: none !important;" in palette
    assert "outline: 2px solid var(--brand-text-secondary) !important;" in palette


def test_visual_qa_covers_all_localized_routes_in_light_and_dark_with_real_mobile() -> None:
    qa = VISUAL_QA.read_text(encoding="utf-8")

    assert 'DARK_VIEWPORTS = (("desktop", 1440, 1000), ("mobile", 390, 844))' in qa
    assert 'page.add_init_script("localStorage.removeItem(\'ilaios-theme\')")' in qa
    assert 'page.add_init_script("localStorage.setItem(\'ilaios-theme\', \'dark\')")' in qa
    assert 'theme="light"' in qa
    assert 'theme="dark"' in qa
    assert "visible_chromatic_ui" in qa
    assert "inspect_navigation" in qa
    assert "mobile navigation panel is too wide" in qa
    assert "header geometry drift" in qa
    assert '"localized_routes":len(ROUTES)*2' in qa

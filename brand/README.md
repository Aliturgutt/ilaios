# ILAIOS Brand Authority

This directory is the canonical repository authority for approved ILAIOS brand assets.

## Rules

- `manifest.yaml` is the machine-readable authority for asset identity, intended use, dimensions, and status.
- Approved visual assets live under `brand/assets/`.
- Original multi-format exports are retained under `brand/source/` when available.
- Product/runtime code must not redefine, redraw, recolor, crop, or creatively reconstruct canonical ILAIOS brand artwork.
- Derived assets must preserve the approved master geometry and brand color system.
- Historical or superseded assets must not be treated as canonical.
- `02-ilaios-primary-horizontal-dark.jpg` is the canonical Dark horizontal logo.
- `13-ilaios-primary-horizontal-light.jpg` is the canonical Light horizontal logo.
- `05-ilaios-app-icon.jpg` is the canonical Dark app icon and dark symbol runtime owner where a symbol/icon is required.
- `04-ilaios-symbol-light.jpg` is the canonical Light symbol/app-icon variant for light surfaces.
- Horizontal UI branding must switch between 02 and 13 according to surface/theme.
- Symbol/app-icon UI usage must switch between 05 and 04 when theme-aware presentation is required.
- Windows executable/MSIX packaging is separate from UI theme switching. `apps/desktop/windows/runner/resources/app_icon.ico` is a non-canonical runtime derivative generated from `brand/assets/05-ilaios-app-icon.jpg` using scale-only transforms.

## Website

The public corporate website should consume approved assets from this authority rather than embedding independently recreated brand graphics.

# ILAIOS Brand Authority

This directory is the canonical repository authority for approved ILAIOS brand assets.

## Rules

- `manifest.yaml` is the machine-readable authority for asset identity, intended use, dimensions, and status.
- Approved visual assets live under `brand/assets/`.
- Original multi-format exports are retained under `brand/source/` when available.
- Product/runtime code must not redefine, redraw, recolor, crop, or creatively reconstruct the canonical ILAIOS symbol.
- Derived assets must preserve the approved master geometry and brand color system.
- Historical or superseded assets must not be treated as canonical.
- `apps/desktop/windows/runner/resources/app_icon.ico` is a non-canonical runtime derivative generated at Windows build time from the canonical `brand/assets/05-ilaios-app-icon.jpg` master using scale-only transforms.

## Canonical master

The approved dark symbol master is `03-ilaios-symbol-dark.jpg`. It is the canonical symbol source for future brand derivations unless `manifest.yaml` explicitly supersedes it.

## Website

The public corporate website should consume approved assets from this authority rather than embedding independently recreated brand graphics.

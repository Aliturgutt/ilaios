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

The approved dark runtime symbol master is `05-ilaios-app-icon.jpg`. `02-ilaios-primary-horizontal-dark.jpg` and `03-ilaios-symbol-dark.jpg` are superseded as runtime owners and are retained only until their final-package reference-board bytes are hydrated.

## Website

The public corporate website should consume approved assets from this authority rather than embedding independently recreated brand graphics.

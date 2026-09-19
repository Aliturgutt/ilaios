# ILAIOS Website V2 — Visual Red-Team and Implementation Scope

Date: 2026-08-18
Branch: `website-v2-redteam`
Production policy: do not merge to `master` or intentionally deploy to production until the full site pass, EN/TR QA, responsive QA, accessibility/SEO checks and final release review are complete.

## Evidence reviewed

The V2 pass is based on the complete desktop screenshot set supplied for the current public website, covering the homepage, Platform, Factories, Capabilities, Security, Explore/Solutions, Enterprise, Individuals, How It Works, ILAIOS Core, Trust Center, Architecture, Documentation, Resources, About and Contact surfaces.

## Red-team findings

1. The current site is coherent but visually reads too much like a technical specification/documentation portal and not enough like a premium product website.
2. The homepage product preview is the strongest element and should become the visual reference for the rest of the system.
3. Repeated thin-border ledgers and numbered rails create excessive wireframe/table density across long pages.
4. Section hierarchy is too uniform: many sections have similar scale, spacing and visual weight.
5. The one-column Explore dropdown is too tall and obscures page content on desktop.
6. Several long canonical chains expose horizontal scrollbars on desktop. Desktop diagrams should fit or recompose; scroll is reserved for genuinely narrow viewports.
7. Interior page heroes need stronger typographic hierarchy without becoming oversized marketing banners.
8. The current visual language should remain flat and geometric: Carbon/Charcoal/Graphite/White with controlled Cyan, no decorative gradients, no glass, no 3D and no decorative shadows.
9. Product truth and CURRENT REALITY / TARGET TRUTH boundaries must not be weakened for marketing aesthetics.
10. Existing route structure, EN/TR parity, semantic controls, accessibility behavior and canonical product terminology remain authoritative constraints.

## V2 design direction

- Product-first homepage with larger, clearer Product Experience composition.
- Editorial spacing and hierarchy instead of repeated card walls.
- Fewer wireframe cues; solid Carbon/Charcoal surfaces with deliberate borders.
- Stronger CTA hierarchy and active states using controlled Cyan.
- Compact two-column Explore mega-menu on desktop.
- Canonical diagrams that fit desktop width without visible horizontal scrollbars.
- Consistent section rhythm across Platform, Factories, Capabilities and Security.
- Cleaner directory treatment for Contact and denser but calmer footer navigation.
- Preserve reusable shared components rather than page-specific one-off styling.

## Implementation status

### Completed in isolated V2 branch

- Added `apps/website/app/website-v2.css` as the global V2 visual override layer.
- Added `apps/website/app/website-v2-tuning.css` for bounded reading width and interior-page typography.
- Activated the V2 layers through `apps/website/app/website-final.css`.
- Improved homepage hero/product-preview scale and spacing.
- Improved header hierarchy and converted Explore to a compact two-column desktop menu.
- Increased product/demo visual priority while keeping the existing canonical prototype truth labels.
- Reworked proof strip and execution protocol rhythm.
- Added V2 treatment for factory explorer, system visuals, governance/evidence controls and canonical diagrams.
- Added desktop canonical-chain fit rules intended to remove visible horizontal scrollbars.
- Improved Contact directory and footer hierarchy.
- Added tablet/mobile V2 recomposition rules without removing existing mobile safety layers.

### Still required before release

- Rebase/sync the V2 branch with the current `master` before integration.
- Run Website CI: site-quality, design benchmark, public UX red-team, lint, typecheck and production build.
- Run native design quality and Web Factory acceptance tests.
- Perform rendered desktop visual QA on every supplied route.
- Perform tablet and mobile rendered QA in EN and TR.
- Verify dropdown/menu keyboard behavior, focus visibility and no overlap.
- Verify every long canonical chain has no unintended desktop horizontal scrollbar.
- Verify all CTA/link targets and EN/TR counterparts.
- Run accessibility, SEO/metadata and responsive overflow checks.
- Perform final Anti-Generic-AI visual red-team.
- Only after the above passes: prepare the final release candidate and production deployment.

## Release rule

No screenshot or architecture direction alone is evidence that a capability is production-ready. Visual redesign must not convert designed/specification language into deployment or availability claims. Production status remains evidence-driven.

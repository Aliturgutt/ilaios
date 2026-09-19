---
name: ilaios-web-accessibility
description: Validate and guide provider-independent web accessibility across semantics, keyboard navigation, focus, names, contrast, forms, motion, touch, responsive layout, and locale parity.
---
# ILAIOS Web Accessibility
Status: IMPLEMENTED
Owner: ILAIOS

## Purpose
Make accessibility a release gate for Web Factory artifacts instead of a cosmetic post-pass.

## Contract
1. Verify semantic structure, headings, landmarks and meaningful controls.
2. Verify keyboard reachability, visible focus, logical focus order and no keyboard traps.
3. Require accessible names, meaningful alternatives and non-color-only meaning.
4. Verify labels, field-local errors, status messaging and recovery paths for forms.
5. Check contrast/readability, zoom/reflow, touch targets and reduced-motion behavior.
6. Test required locales and viewport matrix where the product contract requires them.
7. Fail closed on blocking accessibility evidence gaps; do not infer PASS from source presence alone.

## Evidence
Report observed checks, viewport/locale scope, blockers and reproducible evidence. Automated checks may support but do not replace interaction evidence where required.

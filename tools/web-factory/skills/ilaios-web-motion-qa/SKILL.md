---
name: ilaios-web-motion-qa
description: Provider-independent Run deterministic motion and interaction QA over generated Web Factory output for continuity, jank, fallback, input parity, cleanup, and accessibility.
---
# ILAIOS Web Motion QA
Status: IMPLEMENTED
Owner: ILAIOS

## Purpose
Separate dynamic implementation from proof and reject motion that looks polished but fails under real browser interaction.

## Contract
1. Check scroll jank, pointer tracking continuity, transition interruption, velocity handoff, and spatial continuity.
2. Verify interactive surfaces clean up listeners/state and do not leak behavior across routes.
3. Verify reduced-motion and static showcase fallbacks preserve information and actions.
4. Verify keyboard, pointer, touch/coarse-pointer, and responsive behavior where applicable.
5. Treat runtime performance budget regressions as blocking quality findings when they materially affect interaction.
6. Distinguish source checks, local browser checks, deployment checks, and production checks.
7. Never promote code or a passing unit test to runtime/production verification without matching evidence.

## Evidence
Return explicit PASS/FAIL with route, viewport, input mode, observed defect counts, artifact identity, and evidence references.

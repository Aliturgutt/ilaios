# ILAIOS Native Design Quality System

## Purpose and architecture

`tools/design-intelligence` defines the reusable native skill. `services/design_quality.py` now implements both dependency-free deterministic design strategy and deterministic acceptance evaluation. `GovernedWebFactory.plan_design` reuses the strategy engine and `GovernedWebFactory.accept_design_quality` reuses the assessment gate; neither path creates a second policy engine, router, evidence store, runtime, or Web Factory.

The scoped canonical invariants are recorded in `docs/canonical/WEB_DESIGN_INTELLIGENCE.md` under the parent authority of Product Requirements and System Architecture.

## Adaptive planning model

The native planning path is:

```text
DesignContext
   ↓
NativeDesignStrategyEngine
   ↓
DesignStrategy
   ↓
CompositionFingerprint (when needed for evidence)
```

`DesignContext` contains bounded business, audience, goal, brand, content, complexity, trust, visual-asset, density, locale and device-priority signals. The strategy engine maps this context to inspectable composition, type, spacing, surface, imagery, CTA, diagram, motion, navigation and mobile-transformation behavior.

The engine does not use random layout rotation. Different contexts can deterministically choose different composition families while repeated calls with the same context remain stable.

## Native evaluator families

Browser, accessibility, deterministic probes and governed visual review produce bounded `DesignObservation` rows. The evaluator emits versioned `DesignFinding` evidence and a final `DesignAssessment`. Critical, major and P2 findings block acceptance.

The final-polish assessment covers responsive quality, localization parity, visual quality, typography/readability, component consistency, interaction/accessibility, motion quality, technical-content quality and contextual anti-generic-AI review. It deliberately does not ban gradients, cards, dark backgrounds, large headings or motion by mere presence.

Structural anti-generic evaluation includes a deterministic blocking signal when repeated equal-card groups and repeated centered sections occur together at a level that indicates a generic repeated skeleton. Lower-level decoration signals remain contextual review inputs.

## Evidence and severity

Every finding identifies evaluator/version, route, viewport, category, severity, finding, evidence, recommendation, confidence and status. Invalid or incomplete evidence fails closed. Minor polish observations remain non-blocking only when explicitly dispositioned by project governance.

Required viewport coverage is 320, 360, 390, 412, 430, 768, 1024 and 1440. English and Turkish evidence are both required. Reduced-motion support is part of the blocking quality contract.

## External-reference and licensing policy

Taste Skill, Emil Kowalski's skills and Impeccable may be inspected only as research/provenance references. Their code, prompts, scripts, assets, detectors, templates and runtime are not copied or imported into ILAIOS. Exact external-reference decisions remain recorded in `tools/design-intelligence/PROVENANCE.md`.

This is engineering provenance preparation, not a legal opinion or a declaration that formal licensing review has completed.

## Testing and Website CI gate

`tests/test_design_quality.py` covers clean PASS, blocking FAIL, incomplete coverage, invalid input, deterministic stability, EN/TR, target viewports, contextual anti-generic false-positive resistance, structural-repetition blocking, context-derived strategy stability and differentiation, plus reuse through the canonical Web Factory.

`.github/workflows/website-ci.yml` runs the website policy checks, lint, typecheck, production build and native design/Web Factory tests. Changes to the website, design skill, design evaluator, Web Factory integration or relevant tests trigger the same acceptance workflow.

## Completeness scan

Deterministic automation is appropriate for coverage, overflow, clipping, overlap, contrast results, focus results, target-size results, reduced-motion support and structural repetition signals. Composition quality, brand differentiation, diagram clarity and whether decoration is contextually justified may still require bounded browser/human/LLM observation. Those observations enter structured evidence; an opaque prose-only aesthetic score cannot become acceptance authority.

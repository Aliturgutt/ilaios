# ILAIOS Native Design Quality System

## Purpose and architecture

`tools/design-intelligence` defines the reusable skill and neutral requirements. `services/design_quality.py` implements dependency-free deterministic evaluation. `GovernedWebFactory.accept_design_quality` consumes only the resulting assessment and fails closed; it does not create a second policy engine, router, evidence store, runtime, or Web Factory.

Browser, accessibility, and governed visual review produce bounded `DesignObservation` rows. The evaluator emits versioned `DesignFinding` evidence and a final `DesignAssessment`. Critical, major, and P2 findings block acceptance. Contextual aesthetic signals remain review inputs rather than pretending subjective quality can be inferred from CSS tokens alone.

## Native evaluator families

The final-polish assessment composes responsive quality, localization parity, visual quality, typography/readability, component consistency, interaction/accessibility, motion quality, technical-content quality, and contextual anti-generic-AI review. It deliberately does not ban gradients, cards, dark backgrounds, large headings, or motion by mere presence.

## Evidence and severity

Every finding identifies evaluator/version, route, viewport, category, severity, finding, evidence, recommendation, confidence, and status. Invalid or incomplete evidence fails closed. Minor polish observations remain non-blocking only when explicitly dispositioned by project governance.

## External-reference and licensing policy

Taste Skill, Emil Kowalski's skills, and Impeccable were inspected at pinned revisions for high-level behavior and vocabulary. Their code, prompts, scripts, assets, detectors, and runtime were not copied or imported. Exact revisions, licenses, inspected paths, decisions, and independent implementation evidence are recorded in `tools/design-intelligence/PROVENANCE.md`.

This is engineering provenance preparation, not a legal opinion or declaration of an ILAIOS license. The package is `LICENSING_REVIEW_READY`: its source ownership boundary, dependency inventory, and external-reference decisions are explicit for later formal review.

## Testing and Web Factory gate

`tests/test_design_quality.py` covers PASS, blocking FAIL, incomplete coverage, invalid input, deterministic stability, EN/TR, all target viewports, accessibility interaction, and contextual anti-generic false-positive resistance. `tests/test_web_factory.py` verifies the existing governed artifact workflow; the design gate is exercised directly by the native evaluator tests.

## Completeness scan

Deterministic automation is appropriate for coverage, overflow, clipping, overlap, contrast results, focus results, target size results, reduced-motion support, and structured component-consistency counts. Composition quality, brand differentiation, diagram clarity, and whether decoration is contextually justified still require bounded browser/human/LLM observation. They must be recorded as evidence inputs; they must not be automated through an opaque prose-only score.


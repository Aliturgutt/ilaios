---
name: design-intelligence
description: Evaluate and plan website visual quality, anti-generic-AI risk, typography, spacing, composition, motion, interaction, responsive behavior, EN/TR parity, accessibility visuals, and final polish through ILAIOS-native structured evidence and Web Factory gates.
---

# ILAIOS Native Design Intelligence

Status: IMPLEMENTED
Owner: ILAIOS
Scope: Website and Web Factory design strategy + design-quality evaluation

## Purpose
Plan and evaluate ILAIOS-owned web interfaces without requiring Taste Skill, Emil Kowalski skills, Impeccable, or any other third-party skill at runtime.

## Authority
1. ILAIOS canonical architecture, security, product truth, and brand rules.
2. Repository website engineering standards and verified production evidence.
3. This skill.
4. External design references only as non-authoritative research inputs.

## Adaptive design contract
The Web Factory must not behave as `prompt → generic template → colors/text swap`. Design decisions derive from a structured `DesignContext` and produce an inspectable `DesignStrategy`. Variation is deterministic and reasoned, never random.

Current native structures in `services/design_quality.py`:
- `DesignContext`: business category, audience, primary goal, conversion objective, brand personality, content volume, product complexity, trust requirement, visual asset availability, information density, locale and device priority.
- `DesignStrategy`: primary/secondary composition, type, spacing, surface, imagery, CTA, diagram, motion, navigation and mobile-transformation behavior.
- `CompositionFingerprint`: compact evidence of hero/composition family, section sequence, density, grid patterns and accent distribution.
- `NativeDesignStrategyEngine`: deterministic context-to-strategy planning using a reusable composition vocabulary rather than static template rotation.

Composition vocabulary includes editorial split, technical flow, layered architecture, narrative scroll, product showcase, minimal institutional, visual portfolio, structured comparison, process pipeline, evidence/trust, documentation-led and media-led families. These are composition families, not rigid themes.

## Required evaluation families
- Typography: scale, line length, hierarchy, readable density, brand-font consistency.
- Spacing: section rhythm, component padding, grid gaps, alignment, intentional whitespace.
- Composition: hero proportion, visual hierarchy, grouping, scan path, technical-diagram legibility.
- Brand/color: ILAIOS palette integrity, contrast, restrained accent use, no arbitrary gradients/glows.
- Motion: meaningful transitions only, consistent duration/easing, no gratuitous reveal motion, reduced-motion support.
- Interaction: visible hover/focus/pressed states, touch targets, menu behavior, affordance truthfulness.
- Responsiveness: 320/360/390/412/430px, tablet, desktop; no overflow, clipping, overlap, or broken composition.
- Accessibility-aware visual rules: contrast, focus visibility, readable text size, keyboard-operable controls.
- Browser QA: production route, interaction, navigation, metadata, and responsive checks.
- Visual QA: anti-generic-AI review, hierarchy, rhythm, density, consistency, EN/TR parity.

## Anti-generic-AI checks
Review context + frequency + purpose + composition. Flag oversized vague heroes, universal center alignment, repeated equal-height cards, card walls, card-inside-card structures, universal pill styling, decorative icon tiles without meaning, arbitrary gradients/glows, repetitive marketing layouts, weak CTA hierarchy, gratuitous motion and mobile layouts that merely stack desktop composition. The evaluator also has a deterministic blocking signal for combined repeated equal-card groups and repeated centered sections.

## Dynamic does not mean random
Do not randomly reorder sections, choose colors, change radii, move buttons, or alter type scale merely to claim uniqueness. A law firm, security company, developer platform, restaurant, architecture studio, SaaS company and media brand must be capable of receiving meaningfully different compositions because their structured context differs.

Within one project, preserve typography, spacing, CTA hierarchy, visual language, motion and navigation coherence. Across different projects, allow context-derived composition differentiation.

## Motion rules
Motion must explain state change, hierarchy, continuity, causality or navigation. Prefer transform/opacity when motion is warranted. Avoid universal reveal motion. `prefers-reduced-motion` must be honored. Motion intensity belongs to `DesignStrategy`.

## Execution contract
1. Inspect incumbent brand/design truth before proposing visual changes.
2. Build or validate `DesignContext`; derive a structured `DesignStrategy` rather than arbitrary CSS.
3. Audit the current surface across typography, spacing, composition, brand, motion, interaction, responsiveness, accessibility, browser behavior, and visual quality.
4. Rank findings as critical, major, p2 or minor through the structured evaluator.
5. Apply the smallest coherent root-cause fix rather than layering exceptions.
6. Re-check EN/TR parity and target viewport matrix.
7. Do not modify product claims to solve visual problems.
8. Do not add dependencies solely for visual polish when native CSS/React is sufficient.
9. Do not expand agent/runtime authority.
10. A PASS requires zero critical, major and blocking p2 findings; minor findings require governance disposition.

## Machine contract
- Skill ID: `design.final-polish`; evaluator version: `1.1.0`.
- Planning input: bounded `DesignContext`.
- Planning output: deterministic `DesignStrategy` and optional `CompositionFingerprint`.
- Evaluation input: bounded `DesignObservation` rows for route, locale, viewport, responsive, interaction, accessibility, readability, consistency, decoration, structural repetition and reduced-motion signals.
- Evaluation output: `DesignAssessment` with evaluator ID/version, PASS/FAIL, coverage and structured findings.
- Severity: `critical`, `major`, and `p2` block; `minor` requires explicit disposition.
- Failure: reject empty, malformed, negative, unsupported-locale, or incomplete EN/TR/viewport evidence; Web Factory fails closed.
- Dependencies: Python standard library only. Copied third-party implementation code: NO.

Implementation: `services/design_quality.py`. Tests: `tests/test_design_quality.py`. Integration: `services/integrations/web_factory.py`. Do not replace structured observations with unbounded prose or let an LLM silently choose policy, severity, acceptance or deployment authority.

## Web Factory reuse
Web Factory consumes the same native strategy engine through `GovernedWebFactory.plan_design` and the existing evaluator through `GovernedWebFactory.accept_design_quality`. Do not duplicate policy, routing, evidence storage or skill runtime.

## IP / provenance boundary
ILAIOS owns this implementation. No third-party design-skill code, prompts, templates, detectors, scripts or runtime logic are copied into this skill. External references may inform high-level research only and must not become runtime dependencies. Formal licensing conclusions remain outside this engineering document.

---
name: design-intelligence
description: Evaluate website visual quality, anti-generic-AI risk, typography, spacing, components, motion, interaction, responsive behavior, EN/TR parity, technical-content readability, accessibility visuals, and final polish through ILAIOS-native structured evidence and Web Factory gates. Use for website design audits, production visual acceptance, responsive/localization QA, or Web Factory design-quality decisions.
---

# ILAIOS Native Design Intelligence

Status: IMPLEMENTED
Owner: ILAIOS
Scope: Website and future Web Factory design-quality evaluation

## Purpose
Evaluate and improve ILAIOS-owned web interfaces without requiring Taste Skill, Emil Kowalski skills, Impeccable, or any other third-party skill at runtime.

## Authority
1. ILAIOS canonical architecture, security, product truth, and brand rules.
2. Repository website engineering standards and verified production evidence.
3. This skill.
4. External design references only as non-authoritative research inputs.

## Required evaluation families
- Typography: scale, line length, hierarchy, readable density, brand-font consistency.
- Spacing: section rhythm, component padding, grid gaps, alignment, intentional whitespace.
- Composition: hero proportion, visual hierarchy, card density, grouping, scan path, technical-diagram legibility.
- Brand/color: ILAIOS palette integrity, contrast, restrained accent use, no arbitrary gradients/glows.
- Motion: meaningful transitions only, consistent duration/easing, no gratuitous reveal motion, reduced-motion support.
- Interaction: visible hover/focus/pressed states, touch targets, menu behavior, affordance truthfulness.
- Responsiveness: 320/360/390/412/430px, tablet, desktop; no overflow, clipping, overlap, or broken composition.
- Accessibility-aware visual rules: contrast, focus visibility, readable text size, keyboard-operable controls.
- Browser QA: production route, interaction, navigation, metadata, and responsive checks.
- Visual QA: anti-generic-AI review, hierarchy, rhythm, density, consistency, EN/TR parity.

## Anti-generic-AI checks
Flag and review: oversized hero headings, excessive gradients/glows, repeated card-inside-card structures, universal pill styling, decorative icon tiles without meaning, repetitive equal-height marketing cards, weak CTA hierarchy, gratuitous motion, low-contrast gray-on-color copy, large empty sections without narrative purpose, and mobile layouts that merely stack desktop composition.

## Motion rules
Entry motion should generally decelerate; exits should not feel delayed. Do not animate properties that cause layout instability when a transform/opacity treatment can communicate the same state. Motion must explain state change, hierarchy, continuity, or causality. If it does none of these, remove it. `prefers-reduced-motion` must be honored.

## Execution contract
1. Inspect incumbent brand/design truth before proposing visual changes.
2. Audit the current surface across typography, spacing, composition, brand, motion, interaction, responsiveness, accessibility, browser behavior, and visual quality.
3. Rank findings as critical, major, or minor.
4. Apply the smallest coherent set of fixes that removes the root cause rather than layering exceptions.
5. Re-check EN/TR parity and target viewport matrix.
6. Do not modify product claims to solve visual problems.
7. Do not add dependencies solely for visual polish when native CSS/React is sufficient.
8. Do not expand agent/runtime authority.
9. A PASS requires zero critical and zero major findings; minor findings must be fixed or explicitly accepted by project governance.

## Machine contract
- Skill ID: `design.final-polish`; version: `1.0.0`.
- Input: bounded `DesignObservation` rows for route, locale, viewport, responsive, interaction, accessibility, readability, consistency, contextual decoration, and reduced-motion signals.
- Output: `DesignAssessment` with evaluator ID/version, PASS/FAIL, coverage, and structured findings containing route, viewport, category, severity, evidence, recommendation, and confidence.
- Severity: `critical`, `major`, and `p2` block; `minor` requires explicit disposition.
- Determinism: measurable checks are deterministic. Governed visual review supplies bounded observations only where judgment is necessary.
- Failure: reject empty, malformed, negative, unsupported-locale, or incomplete EN/TR/viewport evidence; Web Factory fails closed.
- Dependencies: Python standard library only. Copied third-party implementation code: NO.

Implementation: `services/design_quality.py`. Tests: `tests/test_design_quality.py`. Do not replace structured observations with unbounded prose or let an LLM silently choose severity.

## Web Factory reuse
This skill is intentionally ILAIOS-owned and self-contained. Web Factory consumes it through `GovernedWebFactory.accept_design_quality` without duplicating policy, routing, evidence storage, or skill runtime.


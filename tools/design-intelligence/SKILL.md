---
name: design-intelligence
description: Evaluate and plan website visual quality, anti-generic-AI risk, typography, spacing, composition, motion, direct-manipulation continuity, interaction response, responsive behavior, EN/TR parity, accessibility, forms, navigation, data visualization, layout stability, and final polish through ILAIOS-native structured evidence and Web Factory gates.
---

# ILAIOS Native Design Intelligence

Status: IMPLEMENTED
Owner: ILAIOS
Scope: Website and Web Factory design strategy + design-quality evaluation

## Purpose

Plan and evaluate ILAIOS-owned web interfaces without requiring UI/UX Pro Max,
Taste Skill, Emil Kowalski skills, Impeccable, or any other third-party skill at
runtime.

## Authority

1. ILAIOS canonical architecture, security, product truth, and brand rules.
2. Repository website engineering standards and verified production evidence.
3. This skill.
4. External design references only as non-authoritative research inputs.

## Adaptive design contract

The Web Factory must not behave as `prompt -> generic template -> colors/text
swap`. Design decisions derive from structured `DesignContext` and produce an
inspectable `DesignStrategy`. Variation is deterministic and reasoned, never
random.

Current native structures in `services/design_quality.py`:

- `DesignContext`
- `DesignStrategy`
- `CompositionFingerprint`
- `NativeDesignStrategyEngine`
- `DesignObservation`
- `NativeDesignQualityEvaluator`

Composition families remain contextual rather than rigid themes.

## Required evaluation families

- Typography/readability, contrast, and user text scaling.
- Spacing, clipping, overlap and responsive composition.
- Brand/component consistency.
- Motion purpose and reduced-motion support.
- Immediate/continuous interaction feedback where direct manipulation exists.
- Gesture tracking continuity for pointer/touch-driven controls.
- Interruptible user-driven motion that can retarget from current presented state.
- Continuity between gesture release and settled motion where momentum exists.
- Spatially consistent reversible transitions.
- Reduced-transparency and increased-contrast fallbacks when relevant surfaces require them.
- Keyboard, focus, touch and non-hover-only interaction.
- Accessibility naming and meaningful text alternatives.
- Form labels and field-local validation/error feedback.
- Visible layout stability.
- Navigation hierarchy and predictable route/back behavior.
- Data visualization labels, legends and non-color-only encoding.
- EN/TR parity and required viewport coverage.
- Anti-generic-AI structural repetition review.

## Execution contract

1. Inspect incumbent brand/design truth before proposing visual changes.
2. Build or validate `DesignContext`; derive a structured `DesignStrategy`.
3. Capture bounded `DesignObservation` evidence.
4. Rank findings as `critical`, `major`, `p2`, or `minor`.
5. Fix root causes rather than layering exceptions.
6. Re-check EN/TR parity and target viewport matrix.
7. Treat direct-manipulation and motion checks as applicable evidence, not a mandate to add animation.
8. Do not modify product claims to solve visual problems.
9. Do not add dependencies solely for visual polish when native implementation is sufficient.
10. Do not expand agent/runtime authority.
11. PASS requires zero critical, major and blocking p2 findings; minor findings require governance disposition.

## Machine contract

- Skill ID: `design.final-polish`.
- Evaluator version: `1.3.0`.
- Planning input: bounded `DesignContext`.
- Planning output: deterministic `DesignStrategy` and optional `CompositionFingerprint`.
- Evaluation input: bounded `DesignObservation` rows.
- Evaluation output: `DesignAssessment`.
- Required viewport matrix: 320/360/390/412/430/768/1024/1440.
- Required locales: EN + TR for this evaluator contract.
- Dependencies: Python standard library only.
- Copied third-party implementation code: NO.

Implementation: `services/design_quality.py`.
Tests: `tests/test_design_quality.py` and
`tests/test_design_intelligence_extension.py`.
Integration: `services/integrations/web_factory.py`.

The Web Factory reuses the same native strategy engine and acceptance gate. No
parallel policy, routing, evidence storage, or skill runtime is introduced.

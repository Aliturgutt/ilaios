---
name: ilaios-frontend-design-review
description: Review or shape frontend interfaces for task clarity, design-system fidelity, accessibility, responsive behavior, state coverage, trustworthy errors, and context-appropriate visual quality. Use for UI implementation or review.
---

# ILAIOS Frontend Design Review

Canonical ID: `ilaios.skill.frontend.design-review.v1`
Methodology contract: `ILAIOS-METHODOLOGY-FRONTEND-REVIEW-V1`

## Authority boundary

This is an instruction-only quality methodology. It does not approve releases, mutate code, grant tools, or replace the existing design-quality, accessibility, runtime, policy, evidence, or independent-review authorities.

## Review sequence

1. Identify the user task, primary action, required states, and intended device/context.
2. Use supplied design-system, brand, component, and product evidence. Never invent design tokens, Figma values, or brand rules that were not provided.
3. Evaluate action hierarchy, navigation/escape paths, onboarding/defaults, loading/empty/error/success/disabled states, and whether the next step is obvious.
4. Evaluate responsive reflow, keyboard use, focus visibility, semantic structure, text scaling, reduced-motion behavior where motion exists, contrast, and error recovery.
5. Evaluate implementation consistency and context-specific visual character without forcing ILAIOS corporate branding onto customer products.
6. Classify findings as blocking, major, or minor and attach observable evidence plus remediation intent.
7. Require runtime/browser evidence for claims that depend on rendered behavior. Static code inspection cannot certify responsive or interaction behavior by itself.

## Trustworthy interface rules

Errors must explain a recoverable next action when one exists. Generated or uncertain content must not be presented as verified fact. Destructive actions require explicit affordance and must remain behind the normal approval/policy path.

## Output expectations

Return prioritized findings, affected surface/state, evidence, rationale, and bounded remediation. Do not self-certify the implementation.

See `references/acceptance-criteria.md`.

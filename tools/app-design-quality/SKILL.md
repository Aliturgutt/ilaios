---
name: app-design-quality
description: Evaluate native desktop and mobile app visual quality, platform adaptation, semantics, focus, interaction states, navigation, safe areas, text scaling, deep links, data visualization, dialogs, responsive layouts, motion, component consistency, and anti-generic-AI risk through ILAIOS-native structured evidence and the App Factory acceptance gate.
---

# ILAIOS Native App Design Quality

Status: IMPLEMENTED
Owner: ILAIOS

Evaluate ILAIOS-owned app clients without third-party design skills or runtime
dependencies.

## Apply the workflow

1. Declare the supported platform/form-factor matrix; do not imply unimplemented
   targets.
2. Inspect real builds on every declared surface.
3. Record bounded `AppDesignObservation` evidence.
4. Run `NativeAppDesignQualityEvaluator.evaluate`.
5. Send the assessment through `AppFactory.accept_design_quality`.
6. Fix blocking findings at their root and repeat the same matrix.

## Required quality families

- clipping, overlap and form-factor adaptation;
- semantics, accessible names, visible focus and focus traversal;
- hover/focus/pressed/selected/disabled/loading/error states where applicable;
- touch target size and touch spacing;
- contrast and component/token consistency;
- navigation adaptation and predictable back behavior;
- platform safe areas/system insets;
- dialogs/sheets, focus containment and safe dismissal;
- text scaling/dynamic type;
- declared deep-link route/state behavior;
- data-visualization labels and non-color-only encoding;
- platform reduced-motion preference;
- contextual anti-generic-AI review.

## Machine contract

- Evaluator ID: `design.app-final-polish`.
- Version: `1.1.0`.
- Severity: `critical`, `major`, and `p2` block acceptance; `minor` requires
  explicit disposition.
- Evidence coverage fails closed when any caller-declared
  platform/form-factor surface is missing.
- Validation rejects empty, malformed, negative, undersized, or unsupported
  evidence.
- Assessment cannot mutate client code, deploy, sign, submit, grant policy, or
  create evidence authority.
- Dependencies: Python standard library only.
- Copied third-party implementation code: NO.

Implementation: `services/app_design_quality.py`.
Tests: `tests/test_app_design_quality.py` and
`tests/test_design_intelligence_extension.py`.
Gate: `AppFactory.accept_design_quality`.

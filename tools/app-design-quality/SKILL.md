---
name: app-design-quality
description: Evaluate native desktop and mobile app visual quality, platform adaptation, semantics, focus, interaction states, navigation, dialogs, responsive layouts, motion, component consistency, and anti-generic-AI risk through ILAIOS-native structured evidence and the App Factory acceptance gate. Use for Flutter or other native app design audits, client build acceptance, form-factor QA, accessibility review, or App Factory design-quality decisions.
---

# ILAIOS Native App Design Quality

Evaluate ILAIOS-owned app clients without third-party design skills or runtime dependencies.

## Apply the workflow

1. Declare the supported platform/form-factor matrix; do not imply unimplemented targets.
2. Inspect real builds on every declared surface.
3. Record bounded `AppDesignObservation` evidence for layout, semantics, focus, interaction states, touch targets, contrast, navigation adaptation, dialogs/sheets, component consistency, motion, and contextual decoration.
4. Run `NativeAppDesignQualityEvaluator.evaluate` with the declared matrix.
5. Send the assessment through `AppFactory.accept_design_quality`.
6. Fix blocking findings at their root and repeat the same matrix.

## Judge native app quality

- Adapt navigation and information density intentionally for compact, tablet, and wide surfaces.
- Preserve visible, logical focus traversal and native semantic roles and labels.
- Provide applicable hover, focus, pressed, selected, disabled, loading, empty, and error states.
- Size touch targets safely and prevent clipping, overlap, unsafe dialog sizing, or unreachable dismissal.
- Honor platform reduced-motion preferences.
- Use one established component/token language; flag repetitive ornamental treatments that lack product meaning.
- Treat platform conventions as interface constraints, never as authority to bypass ILAIOS governance.

## Enforce the machine contract

- Evaluator ID: `design.app-final-polish`; version: `1.0.0`.
- Severity: `critical`, `major`, and `p2` block acceptance; `minor` needs explicit disposition.
- Evidence coverage: fail closed when any caller-declared platform/form-factor surface is missing.
- Validation: reject empty, malformed, negative, undersized, or unsupported evidence.
- Authority: assessment cannot mutate client code, deploy, sign, submit, grant policy, or create evidence authority.
- Dependencies: Python standard library only. Copied third-party implementation code: no.

Implementation: `services/app_design_quality.py`. Tests: `tests/test_app_design_quality.py`. Gate: `AppFactory.accept_design_quality`.

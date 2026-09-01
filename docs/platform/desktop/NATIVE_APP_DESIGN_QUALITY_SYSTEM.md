# Native App Design Quality System

ILAIOS uses `design.app-final-polish` as a deterministic acceptance evaluator for native app evidence. It complements the website-only evaluator and consumes no third-party runtime.

The evaluator accepts only explicit platform/form-factor evidence. This prevents a Windows desktop inspection from being presented as Android or iOS proof. Current client claims must remain bounded to surfaces actually built and inspected.

`AppFactory.accept_design_quality` is the sole integration point. It fails closed for unknown evaluators, failed assessments, and blocking findings while preserving the App Factory's review-only boundary. The evaluator cannot mutate app clients, deploy, sign, submit, issue authority, or persist a competing evidence model.

The initial Windows dogfood matrix is `windows:compact` and `windows:wide`, corresponding to the Flutter client's responsive navigation modes. Android and iOS are supported evidence labels, not claims that those clients are implemented or verified.

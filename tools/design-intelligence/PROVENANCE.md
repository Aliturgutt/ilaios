# ILAIOS Design Intelligence — Reference Provenance

Status: CONTROLLED RESEARCH RECORD
Date reviewed: 2026-08-13

ILAIOS does not vendor, install, import, execute, or depend on the following projects at runtime. They were reviewed only as external design-research references. ILAIOS canonical architecture, brand, security, product truth, and repository standards remain authoritative.

## Taste Skill
- Repository: `Leonxlnx/taste-skill`
- Reviewed branch: `main`
- Pinned observed commit: `e988add20dab0fa97d7a76781c48961c8184288e`
- Research themes used: anti-generic-AI review, hierarchy, typography, spacing, density, motion restraint, responsive fallbacks.
- Integration decision: NO runtime dependency; NO required installer; NO authority expansion.

## Emil Kowalski — Skills for Design Engineers
- Repository: `emilkowalski/skills`
- Reviewed branch: `main`
- Pinned observed commit: `78761e1b57f97dce65b983d640c70a68f39e8163`
- Research themes used: animation decision quality, easing/duration reasoning, micro-interactions, interaction states, identifying surfaces that should not animate.
- Integration decision: NO runtime dependency; NO required installer; NO authority expansion.

## Impeccable
- Repository: `pbakaus/impeccable`
- Reviewed branch: `main`
- Pinned observed commit: `bd2535974861db28a9f4a18ec78608488cd868dd`
- Research themes used: design vocabulary, anti-pattern detection, typography/color/spatial/motion/interaction/responsive review, brand-vs-product context.
- Integration decision: NO runtime dependency; NO required CLI/browser extension; NO authority expansion.

## Clean-room rule
ILAIOS-native artifacts must encode independently stated requirements and evaluators rather than copy upstream prose or implementation wholesale. If any external source disappears or changes incompatibly, ILAIOS design-intelligence behavior must remain available from this repository alone.

## Licensing and security rule
Before any external code or substantial expression is ever incorporated, the exact source revision and license must be re-reviewed. External prompts, scripts, installers, MCP tools, extensions, or agents must never be granted ILAIOS credentials, production authority, repository write scope, browser sessions, or secret access merely because they are design references.

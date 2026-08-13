# ILAIOS Native Design Intelligence

This directory is the ILAIOS-owned design-quality package created while finalizing `ilaios.com`.

It is intentionally self-contained: no Taste Skill, Emil Kowalski skill, Impeccable package, CLI, MCP server, browser extension, hosted API, or third-party prompt is required to use the rules in this directory.

## Contents
- `SKILL.md` — governed design-review and repair procedure.
- `rules.json` — machine-readable rule families, viewport matrix, severities, and PASS criteria.
- `PROVENANCE.md` — source-pinned research record and clean-room/no-runtime-dependency decision.

## Current maturity
- Ownership boundary: IMPLEMENTED.
- Design rule specification: IMPLEMENTED.
- Website application: IN PROGRESS on the website-final branch.
- Reproducible website dependency gate: IMPLEMENTED with a committed `apps/website/package-lock.json`; CI verification remains evidence-driven.
- Deterministic executable evaluator: NOT YET VERIFIED.
- Web Factory runtime wiring: NOT YET IMPLEMENTED.

Maturity labels must not be promoted without repository tests/evidence. A later executable evaluator may consume `rules.json`, but it must remain dependency-light and independently testable.

## Required validation before Web Factory integration
1. Run the rule set against `ilaios.com` EN/TR surfaces.
2. Prove viewport coverage at 320, 360, 390, 412, 430, 768, 1024, and 1440 CSS pixels.
3. Prove keyboard/focus and reduced-motion behavior.
4. Prove no critical/major findings remain.
5. Package the same rules for Web Factory without importing external reference repositories.

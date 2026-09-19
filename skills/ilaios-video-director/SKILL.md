---
name: ilaios-video-director
description: Apply admitted Video Factory cinematography intent through the existing canonical CreativeDirection and CinematographyExecutor path without creating a second director or provider execution authority.
---

# ILAIOS Video Director

Use this skill when an admitted Video Factory plan needs explicit cinematography direction before asset planning or generation.

## Canonical execution

This skill reuses the existing ILAIOS `CreativeDirection` contract and `CinematographyExecutor`. It does not implement a parallel scene planner or directing engine.

Translate creative intent into the canonical fields already supported by ILAIOS:

- visual intent,
- shot scale,
- camera angle,
- camera movement,
- lighting,
- palette,
- pacing,
- continuity keys.

Keep actions physically coherent and define a clear settled end state in the underlying shot intent when later continuation matters.

## Boundaries

The skill is read-only. It does not select models/providers, call generation APIs, upload assets, mutate media, authorize spend, approve policy, or certify output.

Provider/model execution remains downstream of normal ILAIOS admission, policy, budget, approval, routing, Tool Gateway, validation, audit, and evidence controls.

See `references/directing-guidance.md` for independently authored directing heuristics.

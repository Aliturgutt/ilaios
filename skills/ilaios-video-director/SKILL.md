---
name: ilaios-video-director
description: Convert an admitted Video Factory objective into bounded provider-neutral creative direction before prompt composition.
---

# ILAIOS Video Director

## Purpose

Turn an already-admitted video objective into a compact creative-direction contract for the canonical Video Factory pipeline.

## Authority boundary

This skill is advisory and read-only. It does not select or invoke providers, upload assets, mutate media, approve work, bypass policy, create jobs, or promote evidence maturity.

## Inputs

- admitted objective
- input mode
- effective duration
- visual treatment
- required ordered action beats
- camera intent
- audio intent
- required ending state
- continuity invariants

## Output

Return a `DirectedVideoBrief` compatible with `src.video_automation.prompting_skills.VideoDirector`.

The output must keep duration as planning metadata rather than embedding infrastructure or API controls into creative prose.

## Rules

1. Keep every requested action observable and bounded.
2. Prefer one coherent camera strategy over contradictory movements.
3. Make the ending state explicit when downstream continuity depends on it.
4. Preserve caller-supplied invariants instead of inventing new identity facts.
5. Do not add provider names, credentials, routes, prices, or deployment assumptions.
6. Do not claim that direction equals generation, validation, or finished-product evidence.

## Failure behavior

Fail closed when required beats or continuity invariants are empty, contradictory, duplicated, or outside the Video Factory duration bound.

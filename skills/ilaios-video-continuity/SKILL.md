---
name: ilaios-video-continuity
description: Build explicit Video Factory continuity state for identity, wardrobe, objects, counts, ownership, screen direction, and ending state so downstream shots cannot treat occlusion or cuts as an implicit reset.
---

# ILAIOS Video Continuity

Use this skill when a scene spans multiple action beats, cuts, references, or continuation generations.

## Contract

Track only explicit caller/admitted state:

- identity and wardrobe invariants,
- product/object geometry and material invariants,
- object ownership/count/open-closed-attached state,
- travel and screen direction,
- required ending state.

## Boundaries

This skill does not inspect generated pixels, certify identity, edit media, or override the independent QA/validation pipeline. It creates the state contract that downstream prompt generation and QA can check.

Contradictory or duplicate invariants must fail closed.

See `references/continuity-guidance.md`.

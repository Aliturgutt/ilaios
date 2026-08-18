---
name: ilaios-video-continuity
description: Build explicit state inheritance across ordered Video Factory action beats so identity and scene invariants cannot silently reset.
---

# ILAIOS Video Continuity

## Purpose

Transform provider-neutral creative direction into a continuity plan that carries the admitted invariant set through every ordered beat.

## Authority boundary

This skill is read-only. It does not generate media, inspect provider responses, mutate assets, select providers, or certify perceptual continuity after generation.

## Inputs

- directed brief identity
- ordered action beats
- continuity invariant keys
- intended final state

## Output

Return `ContinuityPlan` from `src.video_automation.prompting_skills.VideoContinuityPlanner`.

## Rules

1. Every beat inherits the same admitted invariant set unless a future explicit transition contract authorizes a change.
2. Preserve beat order exactly.
3. Never invent identity, wardrobe, object ownership, or environment facts that were not supplied upstream.
4. Keep final-state intent explicit for downstream prompt composition and later QA comparison.
5. Planning continuity is not proof of generated-media continuity; post-generation QA remains independent.

## Failure behavior

Fail closed when upstream direction is malformed or continuity invariants are unavailable.

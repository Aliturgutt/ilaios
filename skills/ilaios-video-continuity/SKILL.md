---
name: ilaios-video-continuity
description: Preserve and advance Video Factory shot continuity through the existing canonical ContinuityState, ContinuityUpdate, and ContinuityTracker contracts without creating a second continuity engine.
---

# ILAIOS Video Continuity

Use this skill when ordered shots must preserve explicit identity, appearance, object, location, lighting, camera, scene, technology, or timeline state.

## Canonical execution

This skill delegates to the existing `ContinuityTracker`.

- `start` admits an initial canonical continuity snapshot.
- `advance` preserves all unspecified state and applies only explicit updates.
- transitions record the changed fields and predecessor shot.

Reference-prompting methodology is used only to improve what explicit continuity facts callers should capture; it does not replace the canonical state model.

## Boundaries

The skill does not inspect generated pixels, infer hidden identity, edit media, or certify output. Independent QA/validation remains authoritative.

See `references/continuity-guidance.md`.

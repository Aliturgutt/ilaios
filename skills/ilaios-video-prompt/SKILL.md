---
name: ilaios-video-prompt
description: Compose a provider-neutral production prompt from governed Video Factory direction and continuity plans.
---

# ILAIOS Video Prompt

## Purpose

Create a deterministic production prompt from a `DirectedVideoBrief` and matching `ContinuityPlan` without acquiring provider authority.

## Authority boundary

This skill cannot select a provider, call a model, upload references, change policy, spend budget, approve execution, or self-certify output quality.

## Inputs

- directed video brief
- continuity plan with matching brief identity
- optional advisory model identifier
- optional validated reference-plan digest

## Output

Return a `PromptPackage` compatible with `src.video_automation.prompting_skills.VideoPromptComposer`.

## Composition rules

1. Preserve the admitted objective and ordered action progression.
2. Carry camera intent, continuity invariants, audio intent, and ending state into the prompt.
3. Keep duration as external execution metadata.
4. Treat model identity as advisory metadata only.
5. Never encode secrets, provider routes, API parameter names, tenant data, or approval state into prompt text.
6. Reject continuity plans that do not match the directed brief identity or invariants.
7. Do not claim generated media exists because prompt composition succeeded.

## Failure behavior

Fail closed on identity drift, continuity drift, malformed upstream contracts, or missing required planning state.

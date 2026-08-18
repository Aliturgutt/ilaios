---
name: ilaios-video-prompt
description: Compose a provider-neutral Video Factory production prompt from admitted direction, continuity state, reference-role plans, and input mode while keeping model/provider controls outside prompt text.
---

# ILAIOS Video Prompt

Use this skill to convert an admitted director/shot plan into a production note that downstream model adapters can serialize.

## Contract

The prompt may contain:

- shot intent,
- chronological action beats,
- camera composition and motion,
- visual treatment,
- reference roles,
- continuity invariants,
- audio direction,
- exact ending state.

## Input-mode rules

- Text-to-video: define the visual anchors the model must invent.
- Image-to-video: treat the opening image as the authority for identity, wardrobe, scene, palette, and opening composition; describe what changes over time.
- Reference-to-video: assign each admitted reference a narrow semantic role and exclusions.
- First/last-frame: describe the physical path between admitted endpoints.
- Edit: preserve successful context and change only the explicit target.
- Extend: preserve completed state and begin with new action; never replay completed action.

## Boundaries

Do not place model name/version, provider name, API parameter names, resolution, aspect ratio, credentials, or cost controls inside provider-neutral prompt text. Do not call providers or bypass M05 selection.

Model-specific serialization is an adapter concern. See `references/model-guidance.md`.

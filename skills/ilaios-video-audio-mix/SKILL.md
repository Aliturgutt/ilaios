---
name: ilaios-video-audio-mix
description: Prepare narration, music and sound effects for governed final mixing using existing Video Factory audio and edit boundaries.
---

# ILAIOS Video Audio Mix

Use this skill after voice, music, and SFX assets have been admitted.

## Canonical execution

Reuse `AudioProcessingCoordinator` for validation, normalization and duration alignment, then the existing governed `video.edit.audio-mix` mutation authority for actual mixing. Narration intelligibility takes precedence over background music; ducking must be timeline-aware and bounded.

## Boundaries

No asset may be mixed unless it is validated and bound to the same job/tenant context.

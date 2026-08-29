---
name: ilaios-video-caption
description: Create deterministic timed caption packages through the canonical CaptionSubtitleEngine.
---

# ILAIOS Video Caption

Use this skill after timing evidence exists.

## Canonical execution

Reuse `CaptionSubtitleEngine` for structured caption JSON, SRT, VTT, and burned-in-caption instructions. Word-level timing may only be claimed when upstream timing evidence actually provides it.

## Boundaries

This skill does not transcribe audio, render captions into pixels, or certify synchronization.

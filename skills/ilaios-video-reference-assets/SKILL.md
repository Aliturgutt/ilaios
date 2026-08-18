---
name: ilaios-video-reference-assets
description: Convert already-admitted Video Factory reference assets into deterministic semantic control roles, preservation rules, exclusions, and content-bound plans without ingesting, uploading, or dispatching asset bytes.
---

# ILAIOS Video Reference Assets

Use this skill after the authenticated reference-asset boundary has admitted assets and before prompt/model routing.

## Contract

For each reference, define:

- stable reference ID,
- media kind: image, video, or audio,
- the narrow property it controls,
- properties that must be preserved,
- properties that must not leak into generation,
- content digest when supplied by the canonical asset pipeline.

## Boundaries

This skill never reads arbitrary filesystem paths, uploads files, stages URLs, bypasses tenant ownership, or sends media to a provider. Asset bytes and signed/staged transport remain under the existing authenticated reference-asset, Tool Gateway, policy, provenance, and provider runtime boundaries.

Reject conflicting preserve/exclude rules, duplicate reference IDs, and duplicate content digests.

See `references/reference-role-guidance.md`.

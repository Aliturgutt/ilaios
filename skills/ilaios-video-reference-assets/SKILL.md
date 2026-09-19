---
name: ilaios-video-reference-assets
description: Surface already-admitted tenant-bound Video Factory reference metadata through the canonical reference-asset boundary without introducing another uploader, store, analyzer, or provider transport path.
---

# ILAIOS Video Reference Assets

Use this skill only after the canonical reference-asset admission path has accepted and bound reference assets to the request.

## Canonical execution

The skill reuses existing `ReferenceAssetRecord` metadata and the established private reference-asset storage/admission pipeline. It does not read arbitrary filesystem paths or create another asset store.

Relevant admitted metadata includes:

- stable asset ID,
- content SHA-256,
- MIME type and dimensions,
- canonical reference role,
- bounded user instruction,
- tenant/principal binding already enforced by admission.

The existing reference-aware Video runtime remains responsible for private visual analysis, frozen reference briefs, provider conditioning, raw-byte retention/release, and provider execution.

## Boundaries

No raw bytes are read by this skill facade. No upload, URL staging, provider dispatch, ownership bypass, or tenant bypass is added.

See `references/reference-role-guidance.md`.

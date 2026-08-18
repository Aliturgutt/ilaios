---
name: ilaios-video-reference-assets
description: Validate and role-bind Video Factory reference assets before any upload, staging, provider dispatch, or generation.
---

# ILAIOS Video Reference Assets

## Purpose

Convert admitted reference-asset metadata into a bounded immutable `ReferencePlan` for downstream Video Factory use.

## Authority boundary

This skill does not read arbitrary files, upload assets, create public URLs, choose provider payload shapes, dispatch provider requests, or bypass tenant/provenance checks.

## Supported roles

Identity, wardrobe, product, environment, opening frame, ending frame, motion, camera, and audio.

## Rules

1. Every asset requires a stable asset ID, SHA-256 digest, explicit role, and one or more controlled properties.
2. Duplicate asset IDs and duplicate content digests are rejected.
3. Opening-frame and ending-frame roles are singular.
4. The plan is bounded to the canonical Video Factory input limit and must never expand the caller's admitted asset set.
5. Exclusions describe properties that must not transfer from a reference.
6. The resulting plan is content-addressed and provider-neutral.
7. Provider-specific outbound reference limits remain the responsibility of the canonical provider adapter and policy path.

## Output

Return `ReferencePlan` from `src.video_automation.prompting_skills.ReferenceAssetPlanner`.

## Failure behavior

Fail closed on duplicate content, malformed digest, conflicting singular roles, missing control semantics, or limit violations.

# ILAIOS Video Prompting Skills — Provenance

## Ownership and implementation

- FIRST-PARTY ILAIOS IMPLEMENTATION
- INDEPENDENTLY AUTHORED
- CODE/TEXT IMPORTED = NONE
- OWNER = ILAIOS
- NATIVE LICENSE ID = LicenseRef-ILAIOS-Proprietary

## External research reference

Research reference: `Square-Zero-Labs/video-prompting-skill` at commit
`e596f57274c47540d0d215fea9afe361079f2354`.

Upstream repository license observed at research time: Apache-2.0.

The upstream project was used only to study general prompting methodology and
workflow decomposition, including model/input-mode awareness, image-to-video
anchoring, explicit reference roles, temporal continuity, end-state planning,
and character-consistency workflows.

No upstream source code, prompt-guide prose, templates, assets, or implementation
files are included in these ILAIOS-native skills.

## Canonical-component rule

The five skill packages do **not** install parallel Video Factory engines.

- `ilaios-video-director` reuses the existing `CreativeDirection` /
  `CinematographyExecutor` path.
- `ilaios-video-prompt` reuses `ShotPromptCompiler`.
- `ilaios-video-reference-assets` reuses the existing admitted
  `ReferenceAssetRecord` boundary and reference-aware runtime.
- `ilaios-video-model-fit-analysis` reuses `RoutingIntelligenceEngine` for ranking
  evidence only; final routing authority remains canonical `route_model`.
- `ilaios-video-continuity` reuses `ContinuityTracker`.

The governed facade only validates skill admission through the existing
`SkillRegistry` before delegating to these canonical components.

Policy, approval, budget, tenant, Tool Gateway, routing authority, validation,
audit, evidence, and provider execution boundaries remain unchanged.

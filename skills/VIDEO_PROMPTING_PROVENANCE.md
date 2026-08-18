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
files are included in these ILAIOS-native skills. ILAIOS contracts, naming,
governance integration, algorithms, tests, and skill instructions were authored
for the existing ILAIOS Video Factory architecture.

## Authority boundary

These skills do not create a new Core, orchestrator, provider registry, provider
selector, policy engine, approval engine, evidence store, routing authority, or
execution runtime.

The model-fit-analysis output is advisory capability filtering only. Canonical
M04 provider capability state and M05 `ProviderSelectionEngine`, together with
normal policy, approval, budget, tenant, Tool Gateway, validation, audit, and
evidence controls, remain authoritative for execution.

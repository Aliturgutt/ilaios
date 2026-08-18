# Model guidance

This file captures independently authored, provider-replaceable prompting heuristics learned from public model documentation and reference implementations. It is guidance for preparing admitted shot intent; it is not a second prompt compiler or provider execution authority.

## Cross-model invariants

- Choose input mode before preparing shot intent.
- Image-to-video should animate the admitted anchor rather than redesign it.
- Reference-driven generation should give each admitted reference a narrow semantic role and avoid unrelated transfer.
- Long or complex shots should use chronological state transitions and a deliberate ending state.
- Camera direction should include composition, movement, motivation, and stopping point.
- Audio intent should align with visible causes and dialogue/performance beats when the downstream adapter supports native audio.
- Provider/model controls remain outside canonical `ShotPromptCompiler` output unless a governed downstream adapter requires explicit schema fields.

## Provider-family research notes

Public documentation for Seedance 2.x, Veo 3.x, Wan 2.x, LTX 2.x, and MiniMax H3 demonstrates materially different input modes and formatting constraints. ILAIOS therefore keeps those constraints in replaceable provider adapters/catalog evidence instead of hard-coding them into the canonical prompt compiler.

Canonical routing intelligence consumes `ProviderCatalogSnapshot` / `ProviderRuntimeSnapshot` evidence and never treats this guidance file as live capability truth.

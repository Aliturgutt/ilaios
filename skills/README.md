# ILAIOS Native Skills

This directory contains reusable, governed ILAIOS-native skills.

A skill is an execution capability used by a governed worker. It is **not** a second runtime, router, policy engine, factory, or source of execution authority.

## Rules

- Active IDs use the `ilaios.skill.*` namespace.
- Skills execute only after normal capability/factory resolution, admission, policy, budget, approval, and routing.
- Skills cannot expand their own permissions.
- Provider/tool dependencies must be explicit and replaceable.
- Native implementations should prefer deterministic, dependency-minimal execution where practical.
- Current maturity must never be promoted beyond repository/runtime evidence.
- Third-party repositories may be researched as references, but external implementation code or assets are not copied into ILAIOS-native skills unless explicitly approved and licensed.

## Current skills

- `ilaios-diagram-design` — deterministic architecture/flow/sequence/state/data/dependency/trust/capability diagrams with SVG/HTML output and evidence hashes.
- `ilaios-system-design` — deterministic capacity, scalability, bottleneck, failure, architecture-review and renderer-neutral system-design analysis.
- `ilaios-video-director` — provider-neutral creative-direction planning for Video Factory.
- `ilaios-video-prompt` — provider-neutral video prompt composition from admitted direction, continuity, and reference-role contracts.
- `ilaios-video-reference-assets` — semantic reference-role planning over already-admitted assets; it does not ingest or dispatch media bytes.
- `ilaios-video-model-routing` — deterministic model-capability advice only; canonical M05 provider selection remains authoritative.
- `ilaios-video-continuity` — explicit identity/object/screen-direction/end-state continuity planning.

See `VIDEO_PROMPTING_PROVENANCE.md` for the independently authored provenance and external research boundary of the five Video Factory prompting skills.

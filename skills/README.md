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
- `ilaios-video-director` — bounded provider-neutral creative direction for admitted Video Factory objectives.
- `ilaios-video-prompt` — governed prompt composition from directed briefs and continuity plans.
- `ilaios-video-reference-assets` — content-addressed reference-role planning without provider dispatch authority.
- `ilaios-video-model-routing` — deterministic advisory model-capability matching; canonical M05 retains provider selection.
- `ilaios-video-continuity` — explicit state inheritance across ordered video beats for downstream prompt and QA use.

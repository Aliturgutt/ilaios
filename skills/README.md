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

## Open Agent Skills compatibility

ILAIOS Native Skills remain the canonical internal model. The open Agent Skills folder format is supported only through the additive compatibility boundary in `services/agent_skills_compat.py`.

The compatibility contract is:

```text
Open Agent Skills package
        -> metadata/instruction/resource parsing
        -> UNTRUSTED_CANDIDATE
        -> normal ILAIOS capability resolution
        -> policy / budget / approval
        -> Tool Gateway / governed worker or provider
        -> validation
        -> audit / evidence
```

Portable `SKILL.md`, `scripts/`, `references/`, and `assets/` content never becomes a second execution authority. In particular:

- `allowed-tools` is treated as an external declaration, not an ILAIOS permission grant;
- imported scripts are not executable by the compatibility adapter and fail closed unless a separate governed admission path explicitly authorizes execution;
- import/export does not carry tenant state, credentials, approvals, secrets, policy state, execution grants, runtime authority, or evidence-chain records;
- export emits portable instructions and identity metadata only;
- ILAIOS Core, Policy, Approval, Tool Gateway, Validation and Evidence boundaries remain authoritative.

This preserves portability and reduces vendor lock-in without making ILAIOS dependent on another runtime.

## Current skills

- `ilaios-diagram-design` — deterministic architecture/flow/sequence/state/data/dependency/trust/capability diagrams with SVG/HTML output and evidence hashes.
- `ilaios-system-design` — deterministic capacity, scalability, bottleneck, failure, architecture-review and renderer-neutral system-design analysis.
- `ilaios-video-director` — governed access to the existing canonical CreativeDirection/CinematographyExecutor path.
- `ilaios-video-prompt` — governed access to the existing provider-agnostic ShotPromptCompiler.
- `ilaios-video-reference-assets` — read-only access to already-admitted reference metadata; the existing tenant-bound reference pipeline remains authoritative.
- `ilaios-video-model-routing` — governed RoutingIntelligenceEngine candidate ranking; canonical route_model remains final authority.
- `ilaios-video-continuity` — governed access to the existing ContinuityTracker state/transition path.

See `VIDEO_PROMPTING_PROVENANCE.md` for the independently authored provenance, external research boundary, and canonical-component mapping of the five Video Factory prompting skills.

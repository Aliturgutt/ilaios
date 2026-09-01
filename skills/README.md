# ILAIOS Native Skills

This directory contains reusable, governed ILAIOS-native skills.

A skill is an execution or methodology capability used inside governed ILAIOS paths. It is **not** a second runtime, router, policy engine, factory, approval system, Tool Gateway, or source of execution authority.

## Rules

- Active IDs use the `ilaios.skill.*` namespace where a versioned native identity is required.
- Skills execute only after normal capability/factory resolution, admission, policy, budget, approval, and routing.
- Skills cannot expand their own permissions.
- Provider/tool dependencies must be explicit and replaceable.
- Native implementations should prefer deterministic, dependency-minimal execution where practical.
- Current maturity must never be promoted beyond repository/runtime evidence.
- Third-party repositories may be researched as references, but external implementation code or assets are not copied into ILAIOS-native skills unless explicitly approved and licensed.

The stricter authoring rules in `skills/AGENTS.md` apply throughout this directory.

## Canonical taxonomy and skill creation

Logical taxonomy is owned by `services/skill_taxonomy.py`. Canonical first-party skill creation is owned by `skill-engineering/create` at `tools/skill-engineering/skills/skill-create/` and its fail-closed catalog. The top-level methodology packages below do not create a competing skill-creator, registry, runtime, or promotion authority.

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
- `ilaios-frontend-design-review` — provider-neutral UI task/design-system/accessibility/responsive/state review methodology.
- `ilaios-mcp-builder` — provider-neutral MCP contract, schema, side-effect, auth, pagination, error, and evaluation methodology.
- `ilaios-observability` — provider-neutral correlated telemetry/evaluation/privacy/regression methodology.
- `ilaios-governance` — provider-neutral identity/tenant/capability/policy/approval/provenance/evidence/release review methodology.
- `ilaios-video-director` — governed access to the existing canonical CreativeDirection/CinematographyExecutor path.
- `ilaios-video-prompt` — governed access to the existing provider-agnostic ShotPromptCompiler.
- `ilaios-video-reference-assets` — read-only access to already-admitted reference metadata; the existing tenant-bound reference pipeline remains authoritative.
- `ilaios-video-model-fit-analysis` — governed RoutingIntelligenceEngine ranking evidence only; canonical route_model remains final routing authority.
- `ilaios-video-continuity` — governed access to the existing ContinuityTracker state/transition path.

See `VIDEO_PROMPTING_PROVENANCE.md` for the independently authored provenance, external research boundary, and canonical-component mapping of the five Video Factory prompting skills.

## Canonical execution wiring

The methodology packages do not create new execution identities or permissions. Their versioned contracts are embedded as instruction-only overlays in existing Software Factory primary skills for frontend engineering, integration engineering, runtime QA, code review, and release readiness. Canonical `skill-engineering/create` methodology is referenced by implementation planning for skill-related work. Those primary skills continue to execute through the existing P0 worker bindings and governed runtime.

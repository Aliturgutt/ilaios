# ILAIOS Native Skills

This directory contains reusable, governed, ILAIOS-owned native skills.

A skill is bounded domain knowledge or an execution procedure used through the governed ILAIOS runtime. It is **not** a second runtime, router, policy engine, factory, capability registry, Tool Gateway, audit system, evidence authority, or source of execution permission.

## Independent-authorship rule

External skill repositories may be researched for general ideas, terminology, test approaches, and public standards. Their `SKILL.md` files, prompts, scripts, implementation prose, source code, examples, or assets are **not copied into ILAIOS skills**. ILAIOS skills are independently designed and written for the canonical ILAIOS architecture and have no required runtime dependency on an external skill repository.

## Constitutional boundaries

- Active IDs use the `ilaios.skill.*` namespace where registered by runtime metadata.
- Skills execute only after normal capability/factory resolution, admission, policy, budget, approval, and routing.
- Skills cannot expand their own permissions.
- Skills must not create a second Capability Registry, Planner, Control Plane, Policy Engine, Approval Engine, routing authority, Tool Gateway, Audit Engine, or Evidence Chain.
- Skills must not call providers directly in a way that bypasses canonical provider routing.
- Tool/provider dependencies must remain explicit, governed, and replaceable.
- A skill may declare required capabilities and risk, but declaration is not authorization.
- Native implementations should prefer deterministic, dependency-minimal execution where practical.
- Current maturity must never be promoted beyond repository/runtime evidence.

## Target taxonomy

```text
skills/
├── skill-engineering/
│   ├── create/
│   ├── lint/
│   ├── validate/
│   ├── security-scan/
│   ├── evaluate/
│   ├── benchmark/
│   ├── regression/
│   ├── compatibility/
│   └── promote/
├── factories/
│   ├── web/
│   ├── software/
│   ├── video/
│   └── research/
├── capabilities/
│   └── browser/
└── assurance/
```

Existing ILAIOS-native skills remain in their current paths until a separately tested, backward-compatible migration is justified. The taxonomy is additive; it must not break active imports, manifests, runtime modules, or registered IDs.

## Current ILAIOS-native skills

Existing before this taxonomy branch:

- `ilaios-diagram-design` — deterministic architecture/flow/sequence/state/data/dependency/trust/capability diagrams with SVG/HTML output and evidence hashes.
- `ilaios-system-design` — deterministic capacity, scalability, bottleneck, failure, architecture-review and renderer-neutral system-design analysis.
- `ilaios-routing-intelligence` — bounded routing intelligence that preserves the existing canonical routing authority and does not become a router.
- `ilaios-ui-design` — ILAIOS-native UI design capability.

First taxonomy-aligned definitions on this branch:

- `skill-engineering/create` — independently author new governed ILAIOS-native skills.
- `factories/web/production-qa` — evidence-backed Web Factory QA without self-declaring production status.
- `capabilities/browser/production-verify` — high-risk, approval-bounded browser production verification.
- `assurance/security-review` — adversarial security review that preserves canonical governance authority.

Only skills with independently written ILAIOS definitions and corresponding validation evidence should be promoted into active runtime use.

## Maturity

A file existing under `skills/` proves only that a source definition exists. It does not prove execution, test, runtime, deployment, provider E2E, or production status.

Use the repository-wide maturity model and evidence-first reporting in `AGENTS.md`.

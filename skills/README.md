# ILAIOS Native Skills

This directory contains ILAIOS-owned skill definitions. External skill repositories may be researched for general ideas, terminology, test approaches, and public standards, but their SKILL.md files, prompts, scripts, implementation text, or code are not copied into this repository.

## Constitutional boundaries

A skill is bounded domain knowledge or an execution procedure. It is not an authority layer.

Skills must not:

- create a second Capability Registry, Planner, Control Plane, Policy Engine, Approval Engine, routing authority, Tool Gateway, Audit Engine, or Evidence Chain;
- call providers directly in a way that bypasses canonical provider routing;
- grant themselves tools, filesystem, browser, shell, network, tenant, or credential access;
- downgrade policy, approval, privacy, budget, tenant, audit, validation, or evidence requirements;
- claim production readiness merely because the skill definition exists.

Runtime authority remains with the canonical ILAIOS platform. Skill metadata may declare required capabilities and risk, but declaration is not authorization.

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

Only skills that have an independently written ILAIOS definition and corresponding validation evidence should be added to the active registry.

## Maturity

A file existing under `skills/` proves only that a definition has been implemented in source control. It does not prove execution, test, runtime, deployment, provider E2E, or production status.

Use the repository-wide maturity model and evidence-first reporting in `AGENTS.md`.

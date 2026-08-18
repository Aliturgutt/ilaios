# ILAIOS Skill System

## Scope

This document defines the logical first-party ILAIOS Skill taxonomy. It does not replace the canonical Core, Policy, Approval, Routing, Tool Gateway, Validation, Audit, Evidence, tenant, budget, or security authorities.

## Architectural rule

A skill describes bounded domain behavior and capability requirements. A skill does not grant itself execution permission.

The governed path remains:

`User Intent -> Planner/DAG -> Skill Resolution -> Skill -> Capability Request -> Policy/Tenant/Budget/Risk -> Approval when required -> Tool Gateway -> Worker/Tool/Provider -> Validation -> Audit -> Evidence`

## Canonical logical taxonomy

```text
ILAIOS Skills
|
+-- skill-engineering
|   +-- create
|   +-- lint
|   +-- validate
|   +-- security-scan
|   +-- evaluate
|   +-- benchmark
|   +-- regression
|   +-- compatibility
|   +-- promote
|
+-- factories
|   +-- web
|   |   +-- architecture
|   |   +-- design
|   |   +-- accessibility
|   |   +-- performance
|   |   +-- validation
|   |   +-- production-qa
|   +-- software
|   |   +-- spec
|   |   +-- architecture
|   |   +-- implementation
|   |   +-- test
|   |   +-- review
|   |   +-- release-validation
|   +-- video
|   |   +-- director
|   |   +-- prompt
|   |   +-- reference-assets
|   |   +-- continuity
|   |   +-- generation
|   |   +-- edit
|   |   +-- captions
|   |   +-- composition
|   |   +-- render
|   |   +-- output-verify
|   +-- research
|       +-- planning
|       +-- research
|       +-- source-validation
|       +-- contradiction-check
|       +-- citation-validation
|       +-- synthesis
|
+-- capabilities
|   +-- browser
|       +-- navigate
|       +-- inspect
|       +-- automate
|       +-- e2e
|       +-- visual-qa
|       +-- production-verify
|
+-- assurance
    +-- security-review
    +-- differential-review
    +-- threat-model
    +-- supply-chain-audit
    +-- dependency-audit
    +-- release-readiness
```

## Runtime mapping rule

The taxonomy is logical. Existing governed runtime skills remain in their current physical locations and registries. They are mapped into logical nodes rather than moved or rewritten.

The Web Factory mappings currently represented in code are exact mappings to the canonical native Web registry:

- `factories/web/architecture` -> `ilaios-web-architecture`;
- `factories/web/design` -> `ilaios-web-design`;
- `factories/web/accessibility` -> `ilaios-web-accessibility`;
- `factories/web/performance` -> `ilaios-web-performance`;
- `factories/web/validation` -> `ilaios-web-validation`;
- `factories/web/production-qa` -> `ilaios-web-production-qa`.

The Web taxonomy deliberately does not invent separate `build` or `test` skill owners where the current canonical Web runtime owns execution through the Web adapter and the native validation skill. This avoids overlapping ownership and a parallel execution path.

The Software Factory mappings currently represented in code include:

- `factories/software/spec` -> existing requirements and implementation-planning skills;
- `factories/software/architecture` -> existing architecture-planning skill;
- `factories/software/implementation` -> existing governed engineering skills;
- `factories/software/test` -> existing test-design, test-generation, and runtime-QA skills;
- `factories/software/review` -> existing code-review skill;
- `factories/software/release-validation` -> existing build, release-readiness, and recovery skills;
- selected assurance nodes -> existing security, dependency/provenance, and release-readiness skills.

An empty runtime mapping means only that the logical taxonomy node exists. It must not be interpreted as implementation, verification, deployment, or production evidence.

## Skill engineering lifecycle

The target lifecycle is:

`create -> lint -> validate -> security-scan -> evaluate -> benchmark -> regression -> compatibility -> promote`

Promotion does not imply production verification.

## Provider independence

Provider/model routing is not a Video skill responsibility and is not part of this taxonomy. For example, `factories/video/generation` must express capability, quality, cost, privacy, reference-asset, and output requirements. The canonical router and governance layers choose an eligible provider.

## Shared capabilities

Browser is a shared capability family, not a Factory. Web, Software, Research, or other domain skills may request browser capabilities through governed execution boundaries. Browser skill existence never grants direct browser authority.

Additional shared capability families may be added only when a demonstrated dependency requires them. Do not pre-create speculative filesystem, shell, document, media, or external-service authorities.

## Assurance

Assurance is cross-cutting. It does not become an alternate security authority. Security review, differential review, threat modeling, supply-chain audit, dependency audit, and release readiness must preserve independent review and evidence requirements.

## Physical package contract

New first-party skill packages should use the established ILAIOS package discipline where applicable:

- `SKILL.md`
- `PROVENANCE.md`
- `manifest.yaml`
- `input.schema.json`
- `output.schema.json`
- `evals/`
- focused tests

Tool declarations are requested capabilities only. Policy, approval, tenant, security, Tool Gateway, and runtime admission remain authoritative.

## Current implementation boundary

The logical taxonomy is machine-readable in `services/skill_taxonomy.py`.

The first new Skill Engineering package is `tools/skill-engineering/skills/skill-create/`. Its catalog validates package completeness, provenance, deny-set, allowed tool declarations, schemas, and eval coverage, but it does not provide a side-effect executor.

The current six native Web Factory skills are mapped into the taxonomy without moving or duplicating their runtime ownership.

Other taxonomy nodes without an existing runtime mapping remain target nodes until independently authored packages, tests, integration, and evidence are added.

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
|   |   +-- model-fit
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
    +-- agentic-action-audit
    +-- threat-model
    +-- supply-chain-audit
    +-- dependency-audit
    +-- release-readiness
```

## Runtime mapping rule

The taxonomy is logical. Existing governed runtime skills remain in their current physical locations and registries. They are mapped into logical nodes rather than moved or rewritten.

`skill-engineering/create` is the first Skill Engineering node with explicit governed runtime backing. `skill-create` is provisioned into the existing canonical `GovernedRuntime` under the existing Architect identity `ilaios.agent.engineering.architect.v1`, existing capability `architecture.propose`, and existing permission `repository.read`. Package-declared tools/capabilities remain dependency declarations and cannot widen runtime authority. Independent review remains mandatory.

The runtime allowlist is intentionally explicit. A new Skill Engineering source package does not become executable merely because the catalog discovers it; it must receive a reviewed runtime binding separately.

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
- `factories/software/release-validation` -> existing build, release-readiness, and recovery skills.

The Assurance mappings classify the current native SecurityFactory methodology skills without taking over SecurityFactory execution ownership:

- `assurance/security-review` -> `ilaios-security-review` plus the existing Software Factory security-review gate;
- `assurance/differential-review` -> `ilaios-differential-review`;
- `assurance/agentic-action-audit` -> `ilaios-agentic-action-audit`;
- `assurance/threat-model` -> `ilaios-threat-model`;
- `assurance/supply-chain-audit` -> `ilaios-supply-chain-audit` plus existing Software Factory dependency/provenance gates;
- `assurance/dependency-audit` -> existing Software Factory dependency-governance gate;
- `assurance/release-readiness` -> existing Software Factory release-readiness gate.

A mapping with multiple backing skill IDs is classification only. It does not choose an executor, merge authorities, or bypass the runtime owner responsible for admission and evidence.

An empty runtime mapping means no governed runtime backing is declared for that logical node. A source/spec package may still exist, but the empty mapping must not be interpreted as runtime integration, verification, deployment, or production evidence.

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

Assurance is cross-cutting. It does not become an alternate security authority. Security review, differential review, agentic action audit, threat modeling, supply-chain audit, dependency audit, and release readiness must preserve their existing runtime ownership, independent review, and evidence requirements.

## Physical package contract

New first-party skill packages should use the established ILAIOS package discipline where applicable:

- `SKILL.md`
- `PROVENANCE.md`
- `manifest.yaml`
- `input.schema.json`
- `output.schema.json`
- `evals/`
- focused tests

Tool declarations are requested dependencies only. Policy, approval, tenant, security, Tool Gateway, runtime admission, provider routing, Validation, Audit, and Evidence remain authoritative.

## Current implementation boundary

The logical taxonomy is machine-readable in `services/skill_taxonomy.py`.

The first Skill Engineering package is `tools/skill-engineering/skills/skill-create/`. `services/skill_engineering_catalog.py` validates package completeness, provenance, deny-set, allowed tool declarations, schemas, eval coverage, and source maturity. `services/skill_engineering_runtime.py` is a separate fail-closed admission map that provisions only explicitly approved packages into the existing canonical runtime; it is not a second runtime or registry.

At the current boundary, only `skill-create` has Skill Engineering runtime backing. It is also included in the packaged Windows Desktop sidecar data so source and packaged-runtime composition use the same package content. Other Skill Engineering taxonomy nodes remain source/spec or target-only until they receive their own evidence-backed runtime admission.

The current native Web Factory, Video Factory, and SecurityFactory methodology skills are mapped into the taxonomy without moving or duplicating their runtime ownership.

Runtime testing, post-merge verification, packaged Desktop verification, deployment, and production status remain evidence-gated separately.

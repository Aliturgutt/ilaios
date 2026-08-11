# ILAIOS — Historical Post-Core Roadmap

Status: **RETIRED / HISTORICAL**

This file is retained only for provenance. It previously described the transition from the early Core implementation into Code Intelligence, Knowledge Graph, Project Manager and Core Integration.

It is no longer an active execution authority and must not be used to select the next implementation milestone.

## Why it was retired

The repository has advanced far beyond the state represented by the original document:

- the commercial/product identity is ILAIOS;
- the canonical v1 namespace extends through `PLATFORM.P20` and `RELEASE.R03`;
- durable historical evidence exists for later platform/release work;
- Desktop and Website exist as bounded product-surface workstreams;
- platform services include control-plane, governance, evidence, privacy, observability, operations and deployment implementations.

However, historical milestone/release evidence must not be projected as current production readiness when stronger current evidence contradicts it. The active `dev/openclaw/execution_plan.yaml` recovery package explicitly treats historical `PLATFORM.P05` through `PLATFORM.P20` and `RELEASE.R00` PASS evidence as insufficient for current readiness and records `release_state: NOT_DEPLOYED`. `infra/deployment/ext-e01-prerequisites.yaml` likewise records `deployment_performed: false` and `PREPARED_AWAITING_APPROVALS`.

The previous statement that the next atomic unit was `Code Intelligence - Code Entity Model` is stale, but that does not authorize skipping the current recovery/revalidation gates or inventing post-v1 work.

## Current planning source

For repository-level governance use the evidence-based planning documents under `docs/governance/` only as non-canonical projections:

- `REPOSITORY_AUDIT_2026-08-11.md`
- `CAPABILITY_MATRIX.md`
- `CI_WORKFLOW_AUDIT.md`
- `POST_V1_ROADMAP.md`
- `OPENCLAW_POST_V1_AUTOMATION_PLAN.md`

These files do not override canonical architecture, the implementation specification, milestone manifest, or the active controller/evidence state.

## Safety rule

No agent, automation, developer or planning document may infer current PASS, deployment, production readiness, or a new canonical milestone from this retired roadmap. New post-v1 implementation packages require explicit dependency definitions, bounded scope, validations, evidence requirements, rollback and promotion rules before execution.

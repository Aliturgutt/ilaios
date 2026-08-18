# Skill Engineering Provider Certification

## Scope

This document records the evidence boundary for the five runtime-admitted first-party Skill Engineering packages:

- `skill-create`
- `skill-validate`
- `skill-evaluate`
- `skill-benchmark`
- `skill-regression`

It does not create a second runtime, registry, router, policy engine, approval engine, provider authority, verifier, or evidence authority.

## Governed path

Certification must execute through the existing canonical path:

`Skill Engineering package -> canonical Engineering identity -> PermissionFirewall -> ExecutionGrant -> GovernedRuntime -> governed provider adapter -> persisted route -> IndependentVerifier -> receipt`

Package-declared tools or capabilities never widen runtime authority. The provider/model capability contract may contain only capabilities already admitted by canonical P0 governed-AI bindings or `SKILL_ENGINEERING_RUNTIME_BINDINGS`.

## Required provider evidence

A provider certification is accepted only when one exact revision produces a persisted receipt proving all five target skill IDs, exact provider/model identities, immutable skill SHA-256 values, producer evidence digests, verifier evidence digests, and zero observed provider cost for the automatic free/local certification paths.

The OpenRouter live workflow uses the Production environment secret boundary and fail-closed free-model discovery. Local certification uses the same runtime and receipt harness against real OpenAI-compatible localhost servers.

## Local providers

The local certification workflow exercises two independent OpenAI-compatible implementations:

- `llama.cpp` built from an explicit upstream commit and a SHA-256-verified GGUF fixture;
- `vLLM` through its CPU OpenAI-compatible server image, with the resolved container digest persisted as evidence.

The localhost paths remain subject to the same tenant, capability, usage, grant, runtime, and evidence controls as remote providers.

## Status semantics

Workflow or source existence is not provider evidence. `IMPLEMENTED` means the harness exists. `TESTED` requires the repository gates to pass. `VERIFIED` for a provider requires the exact-revision live receipt and matching success commit status. Deployment and production flow verification remain separate maturity stages.

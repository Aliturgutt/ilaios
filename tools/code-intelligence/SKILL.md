# ilaios-code-intelligence

## Identity

- Capability: `ilaios-code-intelligence`
- Family: `code-intelligence-v1`
- Mode: read-only
- Runtime owner: `src.code_intelligence`
- Software Factory adapter: `services.code_intelligence:ILAIOSRepositoryIntelligence`
- External runtime dependency: none

## Purpose

Provide deterministic repository intelligence to governed ILAIOS workflows without granting repository mutation, shell, network, secret, merge, release, or production authority.

This package is a capability-level skill contract. It does **not** add directories to the strict `tools/software-factory/skills` registry. The existing SF-7 skills remain the Software Factory admission surface; this capability supplies their repository-intelligence implementation and typed sub-operations.

## Preconditions

Every execution must have:

1. an admitted repository root;
2. an exact lowercase 40-character Git base SHA;
3. a snapshot whose revision equals that SHA;
4. tenant/actor/policy admission performed by the caller when invoked through Software Factory;
5. bounded query parameters;
6. no request for a forbidden side effect.

Revision mismatch fails closed.

## Skill operations

### `ci-repository-index`

Input: revision-bound `RepositorySnapshot`.

Output: immutable `CodeIntelligenceIndex` with deterministic nodes, edges, coverage, unknowns, schema version, and generation id.

Rules:

- no repository writes;
- no network;
- no persistence in v1;
- no shell from graph builder/engine;
- uncertainty must be preserved.

### `ci-symbol-search`

Input: non-empty symbol query and bounded limit.

Output: ranked deterministic symbol hits.

Rules:

- no embeddings in v1;
- exact/name/prefix/substring ranking only;
- ambiguous execution targets are not auto-selected.

### `ci-call-graph`

Input: unambiguous symbol, `callers|callees`, bounded depth.

Output: bounded traversal over `CALLS` edges.

Rules:

- only statically resolved call edges;
- dynamic calls remain unknown;
- no runtime-completeness claim.

### `ci-dependency-analysis`

Input: indexed file path, forward/reverse direction, bounded depth.

Output: bounded traversal over imports/declared dependencies/other dependency edges.

Rules:

- unresolved targets may be represented only as external dependency nodes;
- no dependency installation or mutation.

### `ci-impact-analysis`

Input: repository snapshot plus changed paths.

Output: existing first-party `RepositoryAnalyzer.impact(...)` result.

Rules:

- do not create a competing impact algorithm inside the graph engine;
- preserve Software Factory validation-profile behavior;
- unknown changed files reduce confidence.

### `ci-architecture-map`

Input: immutable index.

Output: top-level component summaries and cross-component dependency counts.

Rules:

- architecture output is descriptive evidence, not a canonical architecture rewrite;
- grouping is deterministic from repository paths.

### `ci-route-analysis`

Input: non-empty route query.

Output: matching route symbols and same-location handler candidates.

Rules:

- missing route or handler correlation becomes unknown;
- inferred framework routes remain inferred.

### `ci-dead-code-candidates`

Input: immutable index and bounded limit.

Output: non-public callable candidates with no resolved incoming static call.

Rules:

- output certainty is always `INFERRED`;
- output must never say `safe to delete`;
- known route locations are excluded;
- dynamic/reflection/framework/external entry points are explicit residual risk;
- deletion requires normal planning, impact, tests, review, and promotion gates.

### `ci-coverage-check`

Input: immutable index.

Output: total/analyzable/semantic/structural/generated/unknown coverage facts.

Rules:

- semantic ratio is not correctness;
- structural language recognition is not semantic language support;
- external-project language-count claims are forbidden as ILAIOS evidence.

## Canonical deny set

The capability must reject or remain incapable of:

- direct master mutation;
- production mutation;
- governance bypass;
- secret retrieval;
- unrestricted network access;
- third-party source/test/documentation copying;
- automatic deletion based on dead-code candidates;
- generic unbounded graph queries;
- cross-tenant shared persistent graph state without an approved ADR;
- self-certification or self-promotion.

## Evidence requirements

A result should remain bound to:

- repository revision;
- graph schema version;
- generation id;
- certainty;
- explicit unknowns;
- query bounds where a traversal occurs.

## Maturity rule

Files existing in the repository establish implementation evidence only. `TESTED`, `VERIFIED`, `DEPLOYED`, or `PRODUCTION` status requires the normal ILAIOS maturity gates and external evidence; this skill contract cannot self-promote.

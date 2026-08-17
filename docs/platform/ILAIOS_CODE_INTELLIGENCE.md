# ILAIOS Code Intelligence

Status: IMPLEMENTED CANDIDATE — verification and promotion remain governed by CI/evidence gates.

## 1. Purpose

`ilaios-code-intelligence` is the first-party, read-only repository intelligence capability used by the Software Factory. Its job is to convert a revision-bound repository snapshot into deterministic structural evidence that planning, review, validation, and repair workflows can consume without repeatedly rediscovering the entire repository.

This document is subordinate to the canonical ILAIOS architecture, security, implementation, dependency, testing, and governance documents. It does not weaken any admission, policy, tenant, budget, approval, evidence, or promotion gate.

## 2. Clean-room provenance

The design review examined the public behavior and problem framing of `DeusData/codebase-memory-mcp` as an external reference. ILAIOS did not import its source code, tests, documentation text, graph schema, storage format, binaries, or runtime dependencies.

Ideas retained at the problem-domain level were limited to generally applicable concepts: repository indexing, code graphs, symbol lookup, dependency traversal, call relationships, architecture summaries, impact analysis, coverage reporting, and conservative dead-code discovery.

The ILAIOS implementation is independently authored around the existing `src/code_intelligence` models and Software Factory contracts.

## 3. Current reality versus target truth

### Current reality in this change

The repository already had a first-party `RepositoryAnalyzer`, source-file analysis, deterministic `RepositorySnapshot`, dependency extraction, route/schema discovery, test mapping, and change-impact analysis. This change extends that foundation instead of creating a competing code path.

Implemented candidate components are:

- `src/code_intelligence/graph.py` — immutable graph model and deterministic graph builder.
- `src/code_intelligence/engine.py` — bounded typed query engine.
- `services/code_intelligence.py` — clean-worktree, revision-bound adapter compatible with the Software Factory repository-intelligence port.
- `tools/code-intelligence/` — capability contract, skill catalog, provenance record, and machine-readable schemas.
- `tests/test_code_intelligence_graph.py` — graph/query behavior tests.
- `tests/test_code_intelligence_call_resolution.py` — fail-closed call-resolution tests.
- `tests/test_code_intelligence_service.py` — Git/revision-boundary and SF-7 integration tests.
- `tests/test_code_intelligence_contracts.py` — manifest/schema/provenance contract tests.

These files are not PRODUCTION merely because they exist. Their maturity advances only when repository CI, review, and promotion evidence prove the required gates.

### Target truth

The target is a governed repository-intelligence layer that can support Software Factory planning and review while remaining read-only, tenant-scoped, revision-bound, bounded in resource use, and explicit about uncertainty.

Persistent graph storage, embeddings, generic graph-query languages, and cross-repository memory are intentionally outside this v1 implementation. They require separate governance, invalidation, tenant-isolation, privacy, resource-budget, and migration decisions.

An immutable Git-tree reader is also a future hardening target. The current v1 adapter analyzes a live worktree only after clean/tracked-file admission checks and repeats revision/worktree verification after analysis. This materially reduces stale/dirty-tree risk but does not claim a race-free cryptographic binding of every byte read during the scan.

## 4. Integration path

```text
Software Factory request
        |
        v
Identity / tenant / policy / budget / risk admission
        |
        v
RepositoryIntelligencePort
        |
        v
ILAIOSRepositoryIntelligence
        |
        +--> reject symlink / non-root repository path
        +--> validate exact requested base SHA
        +--> verify HEAD == base SHA
        +--> require clean worktree
        +--> capture tracked-file set
        |
        +--> RepositoryAnalyzer.snapshot()
        |       |
        |       +--> files / symbols / dependencies / routes / tests / unknowns
        |
        +--> reject snapshot files not tracked by requested revision
        +--> re-check clean worktree and HEAD == base SHA
        |
        +--> CodeIntelligenceGraphBuilder.build(snapshot)
        |       |
        |       +--> immutable in-memory graph + coverage + generation id
        |
        +--> CodeIntelligenceEngine
                |
                +--> symbol search
                +--> call graph
                +--> dependency analysis
                +--> architecture map
                +--> route analysis
                +--> dead-code candidates
                +--> coverage check

RepositoryAnalyzer.impact(snapshot, changed_files)
        |
        +--> canonical Software Factory change-impact path
```

The intelligence capability does not receive authority to write repository files, merge branches, mutate production, fetch secrets, enable network access, or bypass governance.

Git verification calls are time-bounded and fail closed. Raw NUL-delimited tracked-file output is preserved without whitespace stripping so valid tracked paths are not silently rewritten by the adapter.

## 5. Graph schema

### Node classes

- `file`: a file already admitted into the repository snapshot.
- `symbol`: a snapshot symbol with path, line, type, visibility, and certainty.
- `external_dependency`: a dependency target not represented as an internal file node.

### Edge classes

- `contains`: file contains symbol.
- `parent`: parent symbol contains/nests child symbol.
- `imports`: resolved source import.
- `declares_dependency`: manifest declares external dependency.
- `depends_on`: other typed dependency relationship.
- `calls`: conservatively resolved static call relationship.

Every node and edge is deterministic for the same input snapshot. A `generation_id` hashes the complete graph payload, revision, schema version, and unknown set.

## 6. Call-resolution algorithm

Call resolution deliberately prefers false negatives over false facts.

1. Accept only references already extracted by repository analysis.
2. Ignore unresolved external references rather than pretending they are internal calls.
3. Mark dynamic call expressions as unknown.
4. Resolve an exact unique qualified name first.
5. If a reference is qualified (contains `.`), allow only a unique qualified-name suffix match; if no such match exists, do not fall back to its leaf name.
6. For an unqualified bare name, resolve a unique same-file symbol first.
7. Otherwise resolve a globally unique symbol with that bare name.
8. If multiple internal candidates remain, emit an ambiguity unknown and create no `CALLS` edge.
9. Propagate the weaker certainty of caller and target onto the resulting edge.

This algorithm does not claim runtime call completeness for reflection, dependency injection, generated dispatch, framework magic, callbacks, monkey patching, dynamic imports, or external entry points.

## 7. Query model

The v1 engine exposes explicit typed operations instead of a generic graph-query language. This reduces injection surface, prevents accidental unbounded traversals, keeps evidence auditable, and simplifies policy enforcement.

Queries are bounded by `QueryLimits`:

- maximum result count,
- maximum traversal depth,
- maximum visited nodes.

Invalid, ambiguous, missing, or out-of-contract inputs fail closed with `CodeIntelligenceQueryError`.

## 8. Skill set

The capability catalog defines these first-party skills:

1. `ci-repository-index` — create a revision-bound graph from a repository snapshot.
2. `ci-symbol-search` — deterministic symbol lookup.
3. `ci-call-graph` — bounded caller/callee traversal over statically resolved edges.
4. `ci-dependency-analysis` — bounded forward/reverse dependency traversal.
5. `ci-impact-analysis` — use the existing canonical `RepositoryAnalyzer.impact` path for change blast radius.
6. `ci-architecture-map` — summarize top-level components and cross-component dependencies.
7. `ci-route-analysis` — correlate discovered routes with same-location handlers.
8. `ci-dead-code-candidates` — produce advisory candidates only.
9. `ci-coverage-check` — expose semantic/structural coverage and unknowns.

The existing SF-7 skill family remains authoritative for Software Factory admission. This capability catalog is deliberately outside `tools/software-factory/skills` so the exact 25-skill registry is not silently widened or broken.

## 9. Dead-code safety rule

`ci-dead-code-candidates` must never state that code is safe to delete. A candidate means only that the current static graph has no resolved incoming call under the implemented analysis rules.

Candidates are restricted to non-public callable symbols, exclude known route locations, and are always `INFERRED`. Dynamic/reflection/framework/external use remains a declared risk. Any deletion still requires normal change planning, impact analysis, tests, review, and promotion gates.

## 10. Coverage semantics

Coverage is split instead of collapsed into one misleading percentage:

- `total_files`: all files represented in the snapshot.
- `analyzable_source_files`: non-generated source/test files with recognized languages.
- `semantic_files`: files currently analyzed with Python AST semantics.
- `structural_files`: recognized non-Python files analyzed with bounded structural extraction.
- `generated_files`: generated files represented in the snapshot.
- `unknown_facts`: explicit uncertainty count.

`semantic_ratio` is semantic files divided by analyzable source/test files. It must not be described as repository correctness or language support completeness.

## 11. Red-team findings and controls

| Threat / failure mode | Control in v1 |
|---|---|
| HEAD SHA reported while dirty/untracked worktree bytes are analyzed | Exact base SHA check plus clean-worktree admission before analysis; untracked files fail admission. |
| Ignored supported source enters the live snapshot but is absent from Git revision | Snapshot paths are checked against `git ls-files`; ignored/untracked snapshot files fail closed. |
| Repository changes while analysis is running | Clean-worktree and HEAD checks are repeated after snapshot construction. Residual TOCTOU risk remains until an immutable Git-tree reader exists. |
| Symlinked or nested repository root changes the trust boundary | User-supplied symlink root and non-top-level Git roots are rejected. |
| Git verification hangs | Git verification calls have a fixed timeout and fail closed. |
| Tracked path is corrupted by text trimming | `git ls-files -z` is consumed as raw output; leading/trailing filename whitespace is preserved. |
| False call edges from ambiguous names | Ambiguity produces `unknown`, not an edge. Qualified refs do not fall back unsafely to leaf names. |
| Dynamic-language overclaim | Non-Python structural facts retain inferred/limited semantics. |
| Graph explosion / denial of service | Typed operations plus result/depth/visited-node limits. |
| Generic query injection | No Cypher/SQL/generic graph language in v1. |
| Dead-code false positive causing deletion | Candidate-only, private callable filter, inferred certainty, route exclusion, no mutation authority. |
| Tenant/cross-project graph leakage | No persistent shared graph store in v1; session is in-memory and revision-bound. |
| Persistence invalidation bugs | Persistence deferred until a dedicated ADR defines cache key, tenant partition, invalidation, locking, migration, encryption, and deletion rules. |
| Embedding privacy/cost leakage | Embeddings and external semantic providers are excluded from v1. |
| External-project lock-in | Zero runtime dependency on the inspected reference project. |
| Benchmark laundering | External benchmark claims are not treated as ILAIOS evidence. ILAIOS must measure its own repositories in CI/evals. |
| Repository mutation by intelligence | Graph builder/engine operate on snapshot data; the adapter is read-only. |

## 12. Explicit non-goals for v1

The following are not implemented and must not be presented as current capability:

- persistent cross-run code graph database,
- vector embeddings or neural semantic search,
- generic graph query language,
- 158-language semantic support,
- automatic code deletion,
- autonomous source mutation,
- bypass of Software Factory policy or review,
- immutable Git-object/tree byte reader,
- production deployment or promotion,
- performance claims copied from external projects.

## 13. Promotion criteria

Before this capability can be called VERIFIED, repository evidence must show at minimum:

- unit/integration tests pass,
- strict mypy passes,
- Ruff passes,
- pre-commit/diff hygiene passes where required by repository CI,
- no existing Software Factory skill-registry invariant is broken,
- no runtime dependency on `codebase-memory-mcp` or another external code-intelligence server is introduced,
- deterministic graph tests pass,
- ambiguity, qualified-reference, revision-boundary, and bounded-traversal negative tests pass,
- review confirms that unknown/certainty semantics are preserved.

Only the normal ILAIOS maturity chain and evidence can promote the capability beyond its implemented candidate state.

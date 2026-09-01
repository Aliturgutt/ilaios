# ILAIOS System Design Skill

## Identity

- **id:** `ilaios.skill.system-design`
- **domain:** `architecture`
- **description:** Deterministically converts explicit system requirements and traffic assumptions into capacity estimates, architecture decisions, review findings, failure analysis requirements and a renderer-neutral architecture artifact.
- **execution_class:** `read_only_analysis`
- **risk_level:** `low`
- **side_effects:** `none`
- **rollback:** `not_applicable`
- **evidence_required:** `true`

This skill is advisory and analytical. It does not provision infrastructure, modify a
repository, choose a cloud provider as an authority, spend money, deploy, publish or
bypass ILAIOS governed execution.

## Clean-room provenance

This implementation is original ILAIOS work. No third-party repository source code,
text, diagram, image, schema or implementation has been copied into this skill.
General distributed-systems problem areas may be studied as background knowledge,
but all operational rules, algorithms, schemas, tests and templates in this skill are
written for ILAIOS and are governed by ILAIOS canonical architecture.

## Inputs

At minimum, the skill accepts a bounded `SystemDesignRequest` containing:

- system identifier;
- `concurrent_users` when known;
- `requests_per_second`, or both `concurrent_users` and `requests_per_user_per_second`;
- request and response payload size assumptions;
- `read_ratio` and `write_ratio`;
- `latency_slo_ms` when defined;
- `availability_slo`;
- peak factor;
- measured sustainable RPS per instance when instance sizing is requested;
- budget envelope and measured/quoted cost evidence when a budget decision is requested;
- asynchronous workload fraction when queueing may be relevant.

A statement such as "one million users" is intentionally insufficient for throughput
sizing. Registered users, daily active users and simultaneous users are different
demand models.

## Outputs

The skill produces:

1. explicit assumptions and unresolved demand questions;
2. base and peak RPS estimates;
3. read/write throughput;
4. ingress/egress bandwidth estimates;
5. write-volume estimate;
6. instance-count estimate only when a measured per-instance benchmark is supplied;
7. availability downtime budgets;
8. architecture nodes and edges;
9. architecture decisions with rationale, confidence and evidence status;
10. structured review risks;
11. required verification evidence;
12. a schema-only diagram contract for `ilaios-diagram-design`.

## Preconditions

- Ratios and SLOs must be internally valid.
- Demand must not be fabricated when missing.
- Provider pricing is not assumed to be current unless supplied as evidence.
- A production scalability claim requires representative load-test evidence.
- Security, privacy, tenant isolation and budget controls remain outside this skill's authority and must be enforced by ILAIOS governance during execution.

## Canonical pipeline

```text
USER PROMPT
    -> REQUIREMENTS
    -> ILAIOS SYSTEM DESIGN
    -> Capacity Estimation
    -> Traffic Model
    -> Data Model
    -> Cache Strategy
    -> Queue Strategy
    -> Load Balancing / Overload Protection
    -> Database Scaling
    -> Failure Model
    -> Security Review
    -> Cost / Budget Gate
    -> Architecture Artifact
    -> GOVERNED IMPLEMENTATION
    -> LOAD / FAILURE TEST
    -> EVIDENCE
```

The architecture artifact may describe a service graph containing cycles where the
domain requires them. This must not be confused with the bounded ILAIOS execution
DAG, which must remain acyclic.

## Runtime implementation

Executable code is under `src/system_design/`:

- `capacity_analyzer.py` — demand and capacity calculations;
- `bottleneck_detector.py` — evidence-based saturation and failure-domain warnings;
- `architecture_reviewer.py` — rule-based architecture review;
- `failure_analyzer.py` — failure-mode containment and recovery checks;
- `pipeline.py` — bounded composition into the architecture artifact.

## Rules

The detailed ILAIOS-owned rules are under `rules/`. Important invariants include:

- do not equate account count with concurrency or RPS;
- do not claim scale from estimates alone;
- do not add database sharding without benchmark evidence;
- use bounded retry/backoff and poison-message handling for queued work;
- treat caches as consistency and failure-mode decisions, not free performance;
- high availability requires independent failure domains, not merely more instances;
- budget decisions require current measured or quoted cost evidence;
- no design output may bypass Policy / Trust, approval, budget or evidence gates.

## Diagram integration

`schemas/architecture.schema.json` is the only integration surface required by a
renderer. `ilaios-diagram-design` may consume this artifact without importing this
runtime or becoming an execution dependency. This preserves replaceability and avoids
creating a hidden second architecture authority.

## Verification contract

The following evidence is required before a design can support a production claim:

- representative load test;
- database benchmark for the expected read/write pattern;
- recovery drill or failure injection appropriate to the deployment;
- SLI/SLO telemetry validation;
- cost evidence tied to the intended environment;
- security and trust-boundary review;
- final ILAIOS evidence/provenance record.

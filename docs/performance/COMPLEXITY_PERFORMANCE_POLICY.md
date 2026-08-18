# ILAIOS Complexity & Performance Policy

## Purpose

This policy adds a low-risk performance governance layer without redesigning the architecture, changing Core contracts, or altering authorization, approval, fencing, evidence integrity, or deterministic execution semantics.

## Required order of work

1. Measure before optimizing.
2. Prove a hotspot with repeatable evidence.
3. Prefer bounded, local, reversible changes.
4. Preserve all externally observable behavior and deterministic outcomes.
5. Run correctness gates before performance gates.
6. Keep rollback possible with one independent commit or PR.

## Priority audit surfaces

1. Scheduler
2. Agent / worker routing
3. Tool / capability lookup
4. Event / evidence query paths
5. Memory / search
6. Workflow DAG operations
7. Cost aggregation
8. Desktop projection

The following surfaces are protected and must not be optimized merely for speed: policy, approval, authorization, fencing, and evidence integrity. Changes in those areas require explicit correctness evidence and security review before any performance claim is accepted.

## Complexity guardrails

Hot request-path operations should target O(1), O(log n), O(n), or O(n log n) where practical.

O(n^2) is allowed only when the input is intentionally bounded and the bound is documented and tested.

Exponential or factorial behavior is forbidden on unbounded production execution paths.

Static Big-O classification alone is not a release gate. Runtime evidence is authoritative.

## Performance evidence

A performance change is accepted only when all of the following are present:

- baseline scenario and input size;
- before/after measurements under the same conditions;
- correctness tests passing;
- no contract or deterministic-output change unless separately approved;
- rollback path documented;
- no regression in protected governance/security semantics.

## Benchmark methodology

Use deterministic synthetic fixtures where possible. Prefer operation-count or structural benchmarks for CI stability; wall-clock thresholds may be used only when they have sufficient margin to avoid flaky CI.

At minimum, benchmark representative sizes for the relevant component. For scheduler work, use small, medium, and large worker/lease sets. For DAG work, test the documented task bound as well as smaller cases.

## Red-team stop conditions

Stop and revert the candidate optimization when any of these occur:

- worker selection changes unexpectedly;
- approvals or policy outcomes differ;
- stale fencing tokens become valid;
- evidence ordering, identity, or integrity changes;
- retries or recovery semantics change without explicit approval;
- benchmark gain cannot be reproduced;
- code complexity increases without a material measured benefit.

## Rollout

Performance changes should move through development/test, deterministic regression tests, benchmark evidence, and then staged deployment. Critical runtime optimizations should be feature-flagged or otherwise maintain a compatibility path when practical.

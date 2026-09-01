# ILAIOS Performance Audit

This directory contains the performance-governance foundation for ILAIOS.

The audit layer is intentionally non-invasive: it does not replace runtime components, change Core contracts, or alter policy, approval, authorization, fencing, evidence integrity, or deterministic execution behavior.

## First audit target: scheduler

Run the structural scheduler characterization from the repository root:

```bash
python tools/performance/scheduler_complexity_audit.py
```

Optional scenarios may be supplied explicitly:

```bash
python tools/performance/scheduler_complexity_audit.py \
  --scenario 10:10 \
  --scenario 100:100 \
  --scenario 1000:1000
```

The command emits JSON with:

- worker count;
- seeded active lease count;
- number of `_active_count` invocations;
- number of lease items structurally scanned;
- deterministically selected worker.

The structural counters are preferred for CI characterization because they are deterministic and do not depend on runner speed. Wall-clock benchmarks may be added later as evidence, but they should not use fragile thresholds.

## Workflow for any optimization

1. Capture baseline output.
2. Add or confirm semantic regression tests.
3. Make one local reversible optimization.
4. Run the full test suite and quality gates.
5. Re-run the exact same audit scenarios.
6. Compare before/after evidence.
7. Keep the optimization only when the gain is material and protected behavior remains unchanged.

See `COMPLEXITY_PERFORMANCE_POLICY.md` for guardrails and red-team stop conditions.

# ilaios-skill-benchmark

Benchmark an ILAIOS-native skill candidate across multiple authorized model/provider routes without changing canonical routing authority.

## Purpose

Compare reliability, cost, latency, token use, and other approved metrics across interchangeable execution resources while keeping the skill package constant.

## Required inputs

- validated candidate digest;
- fixed scenario suite;
- approved model/provider route set;
- run count and concurrency bound;
- metric definitions;
- evidence sink.

## Benchmark method

1. Freeze candidate digest and scenario suite for the comparison batch.
2. Resolve each execution resource through canonical routing and governance.
3. Run the configured number of bounded repetitions.
4. Record pass rate and assertion results for every route.
5. Record cost, latency, token, and resource metrics only when measured by trusted telemetry.
6. Preserve per-run evidence and aggregate evidence separately.
7. Report variance and missing measurements explicitly.

## Output

Produce a benchmark matrix keyed by candidate digest, scenario suite, execution resource, run count, success metrics, measured resource metrics, and evidence identifiers.

## Authority rule

Benchmark results may inform routing policy, but this skill does not update routing policy, grant provider access, promote a skill, or declare production readiness.

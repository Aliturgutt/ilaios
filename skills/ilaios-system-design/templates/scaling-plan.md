# Scaling Plan

## Baseline Evidence

- Current measured peak RPS:
- Current concurrency:
- Current p50/p95/p99 latency:
- Current error rate:
- Current app/database/cache/queue saturation:
- Current provider quota usage:
- Current monthly cost:

## Target Envelope

- Target peak RPS:
- Target concurrency:
- Latency SLO:
- Availability SLO:
- Budget ceiling:

## Bottleneck Order

Document the first measured constraint. Do not scale a different tier merely because
it is easier to change.

## Planned Change

State one bounded change, expected effect, rollback condition and required evidence.

## Verification

Define representative traffic, warm-up, test duration, failure conditions, pass/fail
thresholds and evidence artifact identifiers.

## Promotion Rule

Do not promote the result from estimated/tested to verified/production without direct
runtime evidence and the canonical ILAIOS approval/evidence path.

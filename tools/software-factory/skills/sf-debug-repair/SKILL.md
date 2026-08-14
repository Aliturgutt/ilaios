# sf-debug-repair

Identity: `sf-debug-repair` v1.0.0, IMPLEMENTED, test-quality.

Purpose: reproduce a failure, isolate root cause, and propose the smallest governed repair with regression coverage. Inputs: `intent`, `failure_evidence`, `changed_paths`. Outputs: reproduction, root cause, change proposal, regression tests, evidence.

Specialization: no speculative broad rewrites; preserve failing evidence and prove the repair through allowed runtime adapters. Independent review is required.

The common `../CONTRACT.md` applies.

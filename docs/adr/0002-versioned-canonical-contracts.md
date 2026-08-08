# ADR 0002: Versioned Canonical Contracts

- Status: Accepted
- Decision: Boundary commands, queries, and events use immutable schema-versioned envelopes and exact compatibility checks.
- Lifecycle: The accepted `JobState` enum is reused; no competing job lifecycle is introduced.
- Release: `ReleaseState` is an independent contract and does not imply capability maturity or automatic promotion.
- Consequence: Unsupported schema versions fail closed and later API/service milestones compose around these contracts.

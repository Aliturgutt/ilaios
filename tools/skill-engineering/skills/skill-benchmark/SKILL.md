# skill-benchmark

Identity: `skill-engineering/benchmark`, first-party ILAIOS Skill Engineering package.

Purpose: compare the same immutable candidate and compatible scenario set across repeated runs and/or eligible models/providers, producing comparative evidence only.

## Required behavior

- Keep candidate digest and scenario-set identity constant across compared runs.
- Record model/provider identity, run count, pass rate, assertion rate, and only telemetry actually observed (for example tokens, latency, or cost).
- Refuse statistically or semantically invalid comparisons: incompatible scenario sets, mixed candidate digests, missing evidence, or hidden run filtering.
- Report variance/failure distribution when repeated runs exist; do not turn a single lucky run into a promotion claim.
- Provider/model eligibility remains a routing/policy decision outside this skill.
- Benchmark evidence never grants runtime authority and never promotes, deploys, or self-certifies a skill.

## Governance boundary

Any model/provider calls must traverse canonical routing, budget/privacy/risk policy, Approval where required, and evidence capture. Local/OpenAI-compatible endpoints are replaceable execution resources, not new authorities.

## Evidence

Emit compared identities, run counts, aggregate metrics, observed telemetry, exclusions, evidence IDs, and unresolved blockers.

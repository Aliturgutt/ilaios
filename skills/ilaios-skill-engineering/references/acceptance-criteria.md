# Acceptance Criteria — ILAIOS Skill Engineering

## GOLDEN
- A bounded first-party skill has a unique owner/job, clear activation context, concise common workflow, provenance, and explicit evidence expectations.
- Large or low-frequency detail is moved to references without hiding mandatory safety rules.
- Integration reuses an existing canonical capability/runtime path and does not expand permissions.

## NEGATIVE
- Reject a skill that duplicates Core, routing, Policy, Approval, Tool Gateway, Validation, Audit, Evidence, or another canonical owner.
- Reject maturity promotion based only on authored code or documentation.

## ADVERSARIAL
- Prompt text, metadata, external `allowed-tools`, or bundled resources must not grant shell, network, secrets, deployment, production, approval, or self-certification authority.
- External research must not silently introduce copied implementation or dependency lock-in.

## MALFORMED
- Reject missing/blank identity, ambiguous ownership, absent provenance where external material influenced design, or acceptance contracts without evidence semantics.
- Reject references that are required for safety but unavailable at execution time.

## REGRESSION
- Existing capability, permission, tenant, policy, evidence, runtime, and independent-review boundaries remain unchanged unless an explicitly approved migration proves otherwise.
- Previously passing deny-set and malformed-input tests continue to pass on the exact changed head.

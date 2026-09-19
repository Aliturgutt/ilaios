# sf-api-contract

Identity: `sf-api-contract` v1.0.0, IMPLEMENTED, data-contract.

Purpose: classify public API contract changes. Inputs: `intent`, `contract_changes`. Outputs: contract changes, breaking/non-breaking disposition, affected consumers, version/migration need, contract-test requirements.

Specialization: reject silent incompatible changes and require explicit migration/contract-test evidence. Independent review is required.

SF-21 binding: machine-readable API contract changes must pass `services.software_factory_api_contract_safety` on the exact reviewed base/head lineage. Silent breaks are `BLOCK`; intentional versioned breaks and auth/idempotency/behavior-semantic changes preserve `REVIEW_REQUIRED`. The gate is read-only and cannot accept, promote, deploy, publish, or mutate production.

The common `../CONTRACT.md` applies.

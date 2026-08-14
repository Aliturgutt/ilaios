# sf-core-engineering

Identity: `sf-core-engineering` v1.0.0, IMPLEMENTED, engineering.

Purpose: produce bounded canonical ChangeSet proposals for core/domain/platform code. Inputs: `intent`, `changed_paths`. Outputs: change proposal, tests, evidence, unresolved findings.

Specialization: preserve the single canonical Core and governance boundaries; never create a competing Core or edit master/production directly. Python RuntimeAdapter may validate proposed behavior. Independent review is required.

The common `../CONTRACT.md` supplies shared preconditions, deny-set, evidence, failure and completion gates.

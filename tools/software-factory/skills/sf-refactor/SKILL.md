# sf-refactor

Identity: `sf-refactor` v1.0.0, IMPLEMENTED, test-quality.

Purpose: propose behavior-preserving structural improvements. Inputs: `intent`, `changed_paths`. Outputs: change proposal, behavior invariants, tests, evidence, unresolved findings.

Specialization: every structural change must state preserved behavior and regression evidence; refactoring cannot be used to smuggle architecture duplication or unrelated feature work. Independent review is required.

The common `../CONTRACT.md` applies.

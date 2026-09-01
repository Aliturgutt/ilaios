# sf-change-impact-analysis

Identity: `sf-change-impact-analysis` v1.0.0, IMPLEMENTED, core-analysis.

Purpose: classify transitive impact and validation scope for a proposed repository change. Inputs: `intent`, `changed_paths`. Outputs: affected files, symbols, tests and APIs, risk, and validation recommendation.

Specialization: consume canonical SF-5 intelligence and preserve uncertainty when impact cannot be proven. It does not fabricate dependencies or affected consumers.

The common `../CONTRACT.md` supplies governance, deny-set, evidence, failure and completion gates.

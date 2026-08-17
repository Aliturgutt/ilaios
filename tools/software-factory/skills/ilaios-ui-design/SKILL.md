# ILAIOS UI Design

`ilaios-ui-design` is the first-party, deterministic UI-intent resolver used by the governed Software Factory engineering path.

It converts bounded UI intent into `ilaios.ui-spec.v1`: component choice, placement, responsive behavior, interaction constraints, accessibility requirements, design-system policy, quality gates, code-generation constraints, and an explicit zero-authority contract.

The skill does not execute generated code, mutate repositories, retrieve secrets, access the network, select providers, deploy products, or bypass governance. Its structured output is data supplied to the canonical frontend engineering agent and remains subject to existing Software Factory review, design-quality, security, test, and evidence gates.

UI/diagram ambiguity fails closed. Diagram-only intent belongs to `ilaios-diagram-design`. Customer products inherit their existing design system; ILAIOS corporate tokens are selected only when the bounded input explicitly identifies the target product as ILAIOS.

Maturity is `IMPLEMENTED` until CI, integration tests, and master-SHA verification provide stronger evidence.

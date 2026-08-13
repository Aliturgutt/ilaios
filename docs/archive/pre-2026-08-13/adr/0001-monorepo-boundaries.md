# ADR 0001: Monorepo Logical Boundaries

- Status: Accepted
- Decision: Separate projection apps, authoritative services, shared packages, infrastructure, and retained legacy Python domains through explicit dependency-direction rules.
- Context: PLATFORM.P02 requires a reproducible monorepo foundation without prematurely moving proven implementations.
- Consequences: Architecture fitness tests reject forbidden cross-root imports. Later packages may add bounded adapters but may not create competing lifecycle or authority semantics.

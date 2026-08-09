# Unresolved ILATEN to ILAIOS Gaps

## Human decisions required

The following decisions are prerequisites to safe implementation of the remaining canonical controls:

1. Author and approve substantive Section 8 Governance & Operations requirements. The legacy source supplied only an index allocation.
2. Author and approve substantive Section 9 Enterprise Roadmap & Future Evolution requirements. The legacy source supplied only an index allocation.
3. Select supported deployment profiles and their production trust boundaries.
4. Select identity provider, authentication assurance levels, federation, recovery, privileged-access, and break-glass models.
5. Select secret and cryptographic key custody, HSM/KMS boundary, customer-managed-key support, algorithms, cryptoperiods, escrow, destruction, and crypto-agility policy.
6. Define tenant isolation, regional residency, privacy, retention, legal hold, and regulatory/compliance scope.
7. Define SLI/SLO, RPO/RTO, backup, restore, disaster-recovery, incident-response, monitoring, and operational ownership targets.
8. Select container, storage, network, observability, monitoring, and logging deployment profiles and approved technology bindings where implementation-independent controls require concrete enforcement.

Until these decisions are approved through canonical governance, affected requirements remain `MISSING_IMPLEMENTATION` or `PARTIAL` in the migration matrix. They must not be promoted to `IMPLEMENTED` based on documentation or thematic unit tests.

## Matrix totals

- Total normative requirements and gate bullets: 8,250
- `MIGRATED`: 1,933
- `PARTIAL`: 2,749
- `MISSING_IMPLEMENTATION`: 3,568
- `IMPLEMENTED`: 0 (conservative exact-proof standard)
- `MISSING_DOCUMENTATION`: 0 after consolidation
- `CONFLICT`: 0 unresolved after applying the authority hierarchy

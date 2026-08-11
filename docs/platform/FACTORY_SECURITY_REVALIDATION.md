# ILAIOS Factory/Security Revalidation Gate

Status: **PENDING PLATFORM CI**

Scope: revalidate existing ILAIOS Web Factory, Software Factory, Privacy/DLP, and managed cryptography foundations without rewriting working implementations.

## Evidence under test

- `tests/test_web_factory.py` — deterministic governed web artifact creation, integrity validation, tamper rejection, and canonical scope.
- `tests/test_software_factory.py` — isolated proposal/test/review workflow, bounded allowlist, production immutability, and mandatory human review boundary.
- `tests/test_tenant_privacy.py` — tenant isolation, residency, purpose limitation, minimization, DLP, legal hold, retention, and deletion audit lifecycle.
- `tests/test_managed_cryptography.py` — provider-neutral envelope boundary, tenant binding, rotation, revocation, destruction, crypto agility, and cryptoperiod enforcement.
- `tests/test_factory_security_revalidation.py` — cross-capability proof that a governed Web Factory acceptance artifact can enter tenant-scoped privacy/audit context and a tenant-bound managed-crypto boundary while cross-tenant access fails closed.

## Acceptance gate

This package may advance capability maturity only after the branch passes the complete Platform CI suite:

1. pytest full regression
2. Ruff
3. strict mypy
4. scoped pre-commit
5. diff hygiene

No Website or Desktop implementation files are in scope. No cloud/production mutation is authorized by this package.

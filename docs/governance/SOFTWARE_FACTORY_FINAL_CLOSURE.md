# Software Factory — Final Closure Gates

## Closure order

SF-31 is followed by four explicit closure stages:

1. Commercial Licensing Package
2. E2E Acceptance
3. Two-Pass Completeness Scan
4. Final Evidence Reconciliation

None of these stages grants direct promotion, deployment, publication, or production-mutation authority.

## Scope boundary

This closure is scoped to `SOFTWARE_FACTORY_IMPLEMENTATION`: the first-party Software Factory services, governed skill packages, tests, CI gates, and Software Factory evidence/documents. It does not certify the whole ILAIOS product for external commercial distribution and it does not replace release-specific website, desktop, media, provider, store, or production licensing/deployment evidence.

Repository-wide and product-release licensing remains governed by `docs/governance/LICENSE_DECISION.md` and `docs/governance/IP_LICENSE_PROVENANCE_AUDIT.md`. Where those records require release-specific dependency/license inventories or ownership confirmation, those remain separate release gates. Software Factory closure must not convert them into an unsupported legal or deployment claim.

## Commercial Licensing Package

The package reuses SF-13 dependency governance, SF-14 license/IP provenance, and SF-15 SBOM evidence. For the bounded Software Factory implementation, commercial closure requires resolved first-party skill provenance, imported code/text disposition, commercial compatibility, and a content-addressed package manifest. Unknown or unresolved Software Factory dependency licensing is `BLOCK`. AI-generated material must not be automatically described as IP-risk-cleared; provenance and review status are recorded without unsupported legal warranties.

## E2E Acceptance

End-to-end acceptance reconciles the governed Software Factory path from repository analysis and ChangeSet creation through validation, independent review/security, dependency/license controls, SBOM/build/signing, DB/API safety, retry/cost/observability, promotion eligibility, PR/CI, recovery, skill evaluation, red team, and documentation synchronization. Direct production mutation is a hard failure.

## Two-Pass Completeness Scan

Two separately identified passes are required. Pass one covers architecture, capabilities, dependencies, and phase completeness. Pass two independently checks code/tests/CI, documentation, and evidence consistency. Any unresolved finding prevents closure and requires the affected pass to be rerun after remediation.

## Final Evidence Reconciliation

Final reconciliation requires exactly one evidence record for every `SF-0` through `SF-31` phase. Each phase must be both merged and exact-head-CI verified with valid head SHA, merge SHA, deterministic evidence digest, and Git ancestry contained in the final tested head. It also requires the Commercial Licensing Package, E2E Acceptance, and Two-Pass Completeness Scan to have passed.

External blockers such as a CI runner outage, payment failure, or spending-limit restriction remain blockers. They cannot be converted into PASS evidence, skipped, or represented as completed work.

The final reconciler may report Software Factory implementation completion only when all required evidence is present and internally consistent. A CI structural audit of the closure implementation is deliberately weaker: it proves that closure machinery and upstream first-party authorities are present, but it does **not** itself claim final Software Factory completion.

## Authority boundary

Even after a final Software Factory implementation PASS:

- `promotion_authorized = false`
- `deployment_authorized = false`
- `production_mutation_authorized = false`
- whole-product commercial distribution is not implied
- external provider/store/deployment evidence remains capability-specific

This document records engineering evidence and governance boundaries, not legal advice.

# Commercial Identity Closure Workflow

## Purpose

This file is the durable GitHub checkpoint for commercial identity closure across ilaios.com, app.ilaios.com, Desktop, and future app clients. Work is executed serially from the canonical master. A phase is not promoted by documentation alone.

## Non-negotiable execution protocol

For each phase:

1. Re-read canonical `master` and record the exact SHA.
2. Create a bounded feature branch from that SHA.
3. Implement only the phase scope; no Core rewrite and no bypass of Policy Engine, Approval Engine, Tool Gateway, Validation, Audit/Evidence, tenant, entitlement, or security controls.
4. Commit meaningful atomic progress immediately so timeout recovery is GitHub-backed.
5. Run targeted local/unit/integration tests where available.
6. Open/update a draft PR and record exact head SHA.
7. Require exact-head Required CI and all phase-specific gates to PASS.
8. Re-read `master` immediately before merge and reject stale-base merges.
9. Merge only with expected head SHA.
10. Re-read resulting exact `master`, verify exact-master evidence, and only then mark the phase VERIFIED.
11. Start the next phase from the new verified master.

Timeout recovery rule: never reconstruct completed work from chat memory. Re-read branch, PR, head SHA, CI, merge status, and exact master from GitHub and continue from the last durable checkpoint.

## Maturity rule

`DESIGNED -> SPECIFIED -> IMPLEMENTED -> TESTED -> VERIFIED -> DEPLOYED/PRODUCTION`

No step may be skipped without evidence.

## Canonical identity rule

External providers authenticate users; they are not the canonical ILAIOS account key.

Canonical path:

`verified external identity -> immutable provider subject -> Internal User ID -> Tenant -> Membership -> Entitlement -> Session`

All clients must resolve to the same internal User ID/Tenant/Entitlement state.

Automatic account merge by matching email is forbidden. Linking an additional provider requires an already-authenticated ILAIOS session plus a newly verified provider identity. Cross-tenant linking fails closed.

## Supported commercial sign-in targets

Initial commercial set:

- Google
- Microsoft identity platform (Hotmail, Outlook.com, Live, Microsoft 365)
- GitHub
- Verified Email (magic link or one-time verification code; no password requirement for v1)
- Apple
- Enterprise OIDC

Future enterprise extension only when commercially required:

- SAML federation / managed enterprise SSO

## Serial closure phases

### Phase 1 — Central Identity

Target:

`External provider -> immutable provider subject -> Internal User ID -> Tenant`

Acceptance:

- provider-neutral external identity key
- canonical User/Tenant resolution
- authenticated-only provider linking
- no email-based auto merge
- identity takeover denial
- cross-tenant negative tests
- idempotent repeat login/link behavior
- exact-head CI PASS
- exact-master verification after merge

Current checkpoint: merged through PR #705; Phase-1 lineage remains regression-green on canonical master before Phase 2.

### Phase 2 — Production Persistence

Persist at minimum:

- User
- IdentityAccount
- Tenant
- Membership
- Session
- Entitlement

Acceptance:

- migration-safe schema
- unique provider + immutable subject constraint
- tenant isolation
- session revocation support
- entitlement binding
- rollback path
- DB migration tests
- cross-tenant negative tests
- exact-master evidence

### Phase 3 — Google production OAuth

Acceptance:

- production OAuth consent/configuration
- domain verification where required
- separate dev/prod clients
- web redirect allowlist
- Desktop/native PKCE client
- state + nonce validation
- issuer/audience/signature/expiry validation
- first login + returning login + logout + revoked/expired/invalid token E2E
- same Internal User ID across Web/Desktop

### Phase 4 — Microsoft production OAuth

Covers Hotmail, Outlook.com, Live, Microsoft 365 and approved Microsoft organizational identities.

Acceptance mirrors Google plus tenant/account-type policy and real provider E2E.

### Phase 5 — GitHub OAuth

Acceptance:

- production OAuth app
- verified immutable GitHub account identifier
- state validation
- secure code exchange
- same Internal User ID/Tenant/Entitlement mapping
- account linking and takeover-negative E2E

### Phase 6 — Verified Email

Preferred v1: magic link or one-time verification code.

Acceptance:

- short-lived single-use token/code
- hashed server-side token material
- rate limiting
- replay prevention
- email normalization rules
- no unverified-email account linking
- account recovery policy
- E2E and negative tests

### Phase 7 — Apple

Acceptance:

- Sign in with Apple configuration
- Apple stable subject mapping
- private relay email handling without treating email as account identity
- nonce/state verification
- same internal account mapping
- iOS/App Store compatibility evidence when that client is active

### Phase 8 — Account Linking UX/API

Target connected-account view:

- Google
- Microsoft
- GitHub
- Apple
- Email
- Enterprise OIDC when enabled

Acceptance:

- authenticated add/remove flow
- cannot remove last usable sign-in method without recovery path
- recent-authentication requirement for sensitive linking/unlinking
- audit events
- tenant boundary enforcement
- conflict/takeover negative tests

### Phase 9 — Web / app.ilaios.com Session Integration

Acceptance:

- central identity backend
- `HttpOnly`, `Secure`, appropriate `SameSite` cookie policy
- CSRF protection
- CSP/rate limiting as applicable
- logout + revocation
- session rotation
- first/returning login
- same User/Tenant/Plan/Projects/Outputs state
- production browser E2E

### Phase 10 — Desktop Integration

Acceptance:

- existing Authorization Code + PKCE boundary uses central account resolver
- no provider password/raw credential storage
- secure OS credential storage
- token/session expiry and revocation handling
- restart recovery
- same User/Tenant/Entitlement/Projects/Outputs as web
- clean-machine Desktop E2E

### Phase 11 — Entitlement and Billing Binding

Acceptance:

- provider-independent subscription identity
- plan/entitlement resolved from Internal User/Tenant, never provider email
- usage quota
- budget enforcement
- provider spend controls
- cancellation/renewal/failure state behavior
- webhook idempotency and verification
- negative E2E

### Phase 12 — Production Cross-Client Certification

Required positive flows:

- Google -> Web -> same account
- Microsoft -> Desktop -> same account
- GitHub -> App/Web -> same account
- Email -> Web -> same account
- Apple -> supported app/client -> same account when client exists

Required shared state:

- same User ID
- same Tenant
- same Membership/Role
- same Projects
- same Plan/Entitlement
- same Usage/Cost state
- same Outputs/Evidence visibility according to authorization

Required negative flows:

- invalid/expired/revoked token
- replayed state/code
- wrong issuer/audience/nonce
- cross-tenant access
- account-link takeover attempt
- unauthorized unlink
- suspended tenant/user
- exhausted entitlement/budget

Final certification also requires exact deployed SHA, production E2E evidence, rollback proof, monitoring, and audit trace.

## Current reality checkpoint — 2026-08-21

### Phase 1

- Original Phase-1 PR #702 became stale after master advanced and was not merged on stale evidence.
- Current-master successor PR #705 was merged with exact-head gate evidence.
- Phase-1 merge lineage SHA: `1b587fbe649514ac28c4cb39f56eb1f6e073253a`.
- Before Phase 2 started, canonical master was re-read as `2c965fa849df1a3eef1aafd1117dad2bdc7762e6`; Phase-1 lineage remained in ancestry and both `ilaios/required-ci-exact-master` and `ilaios/software-factory-exact-master` were SUCCESS on that exact master.

### Phase 2 — Production Persistence

- Original Phase-2 PR #714 was based on `2c965fa849df1a3eef1aafd1117dad2bdc7762e6` and reached exact-head Required CI + Software Factory Final Evidence PASS at head `3cf51d600b97ee6e99880568a45fa9a5809d7982`.
- Before merge, canonical master advanced to `1e42eec9e8759c0599ea7932c4dd38af23c46c15`; the stale #714 PASS was rejected as merge authority.
- Compare evidence showed the master advance touched only `.github/workflows/desktop-exact-master-status.yml` and `.github/workflows/desktop-exact-master-final-artifact.yml`; there was no path overlap with the reviewed Phase-2 identity/migration delta.
- Successor branch: `identity/production-persistence-current-20260821`, created directly from exact master `1e42eec9e8759c0599ea7932c4dd38af23c46c15`.
- Successor PR: `#718`. Initial replay head before this checkpoint commit: `2308d3930eef1f333198f201f41e4f811dca6c39`.
- PR #714 is closed unmerged and superseded by #718.
- The exact reviewed five-path delta was replayed onto current master: `docs/identity/COMMERCIAL_IDENTITY_CLOSURE_WORKFLOW.md`, `services/central_identity_sqlite.py`, `services/control_plane/migrations.py`, `tests/test_central_identity_sqlite.py`, and `tests/test_web_app_domain_migrations.py`.
- Existing authoritative DB/migration authority remains `services/control_plane/migrations.py`; no second migration engine or identity authority was introduced.
- Schema v9 persists canonical `identity_users`, `identity_accounts`, `identity_tenants`, `identity_memberships`, `identity_sessions`, and `identity_entitlements`.
- Provider identity uniqueness remains `provider + issuer namespace + immutable subject`; verified email is not a merge key.
- Session storage accepts SHA-256 credential digests only and includes revocation state; entitlement state is tenant-scoped.
- Regression coverage includes restart persistence, same-email-no-merge, enterprise issuer namespace, takeover/cross-tenant denial, session revocation/tenant binding, entitlement scoping, and rollback/re-upgrade.
- On successor replay head `2308d3930eef1f333198f201f41e4f811dca6c39`, Software Factory Final Evidence PASS, Web App Factory Continuation Gate PASS, and Required CI was still in progress. Completed Required CI sub-gates already PASS included DB migration safety, secret scanning, API contract safety, supply-chain hardening, operational safety, assurance, structural audit, and change classification; Platform validation/quality and ClamAV remained in progress.
- This checkpoint commit changes the exact PR head again. Therefore all pre-checkpoint PASS results are non-final evidence. Phase 2 remains IMPLEMENTED/TESTING, not VERIFIED, and must not merge until the new exact head produced by this checkpoint has fresh Required CI + Software Factory Final Evidence PASS, canonical master is re-read immediately before merge, expected-head merge succeeds, and exact-master evidence passes.

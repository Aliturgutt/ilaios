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

### Phase 1 — VERIFIED

- Original Phase-1 PR #702 became stale after master advanced and was not merged on stale evidence.
- Current-master successor PR #705 was merged with exact-head gate evidence.
- Phase-1 merge lineage SHA: `1b587fbe649514ac28c4cb39f56eb1f6e073253a`.
- Before Phase 2 started, canonical master was re-read as `2c965fa849df1a3eef1aafd1117dad2bdc7762e6`; Phase-1 lineage remained in ancestry and both `ilaios/required-ci-exact-master` and `ilaios/software-factory-exact-master` were SUCCESS on that exact master.

### Phase 2 — Production Persistence — VERIFIED

- Original Phase-2 PR #714 became stale and was closed unmerged; stale PASS evidence was not reused.
- Current-master successor PR #718 was merged after fresh exact-head Required CI + Software Factory Final Evidence PASS.
- Phase-2 merge/master SHA: `2f165aff5404d9edb38ca1e50d913fe4240dcf6b`.
- Exact-master Required CI + Software Factory evidence passed before Phase 3 began.
- Schema v9 persists canonical User, IdentityAccount, Tenant, Membership, Session and Entitlement through the existing control-plane migration authority.

### Phase 3 — Google production OAuth — IN PROGRESS

- PR #725 reached exact-head Required CI + Software Factory Final Evidence PASS, but master advanced; it was closed unmerged and stale PASS was rejected.
- PR #728 replayed the reviewed Google delta on master `687d307c6a521f68c164b510cf76d34875d242fd` and itself reached fresh exact-head PASS, but master advanced again through non-overlapping Operations/Meta + Desktop workflow-only changes.
- Current canonical master at successor construction: `636547791e1a2cadf6731676a01b13c7feee115b`.
- Current authoritative successor: PR #731, branch `identity/google-production-oauth-current2-20260821`, created directly from that exact master.
- Bounded runtime/test scope: `services/google_oidc.py` and `tests/test_google_oidc.py`; this checkpoint file is the only additional path.
- Google authority remains pinned to official issuer/auth/token/JWKS endpoints; production/development web client IDs must be distinct; production redirects require explicit HTTPS non-loopback exact allowlisting; Desktop/native reuses the existing provider-neutral Authorization Code + PKCE boundary; immutable Google `sub` is the external identity key and verified email remains metadata only.
- PR #728 was closed only after #731 existed. No stale PASS from #725/#728 is merge authority.
- Phase 3 remains IMPLEMENTED/TESTING until PR #731 exact-head Required CI + Software Factory Final Evidence PASS, immediate current-master revalidation, expected-head merge, and exact-master verification complete.
- External acceptance remains unproven and must not be fabricated: Google Cloud OAuth consent/client configuration, domain/redirect registration, production secret/config provisioning where applicable, and real Google Web/Desktop provider E2E.

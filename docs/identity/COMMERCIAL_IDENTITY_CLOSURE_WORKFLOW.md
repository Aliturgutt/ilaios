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

Current checkpoint: PR #705 (current-master successor to stale PR #702).

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

- Original Phase-1 base: `2413595ebc10444a201e26b294456d5fbdb0f851`.
- Original Phase-1 PR #702 exact head `16e32c628a05a08bd7a32a2516668db1c7946522` reached Required CI Gate PASS and Software Factory Final Evidence PASS, but became stale after master advanced by 9 commits.
- Current canonical master for the Phase-1 replay: `cb52de093300881c4864e9f44a2594e175c8c081`.
- Master advance touched Web App Factory/auth-contract and workflow files, not the three Phase-1 paths; stale evidence is still not reused.
- Current Phase-1 branch: `identity/central-account-linking-current-20260821`.
- Current Phase-1 successor PR: `#705`.
- Replay commit before this checkpoint update: `3e7478d50d3b44107ea59634dc217d915c6e26c7`.
- Fresh exact-head Required CI and Software Factory Final Evidence are required on PR #705 before merge.
- Production OAuth, cross-client production auth E2E, production persistence, provider account linking UI, and entitlement/billing E2E are NOT yet certified.
- Vercel build-rate-limit is a separate deployment blocker/noise source and must not be misclassified as identity correctness evidence.

## Status update discipline

When updating this file, preserve its filename and headings. Additive edits are preferred. Never mark a phase VERIFIED unless the exact GitHub/CI/runtime evidence exists.

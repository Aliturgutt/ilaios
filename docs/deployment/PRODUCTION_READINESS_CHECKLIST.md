# Production Readiness Checklist

Status: CONTROLLED

A release may enter production promotion only when every applicable item has evidence or an explicitly approved exception.

## Identity and authorization
- [ ] production account/environment identified
- [ ] least-privilege credentials/OIDC validated
- [ ] secrets exist in approved store; no plaintext secret in repo/logs
- [ ] explicit human approval recorded for production-impacting action

## Build and release
- [ ] source commit and PR identified
- [ ] required CI PASS
- [ ] dependency lock/SBOM/provenance evidence available as applicable
- [ ] immutable artifact digest identified
- [ ] release/changelog entry prepared

## Data and migration
- [ ] migration reviewed and tested
- [ ] backup/restore readiness verified where state changes
- [ ] rollback or forward-fix strategy documented

## Runtime
- [ ] infrastructure/readiness checks PASS
- [ ] health/readiness endpoints defined
- [ ] observability dashboards/alerts active
- [ ] capacity/quota/cost boundary reviewed
- [ ] tenant isolation/privacy/security controls verified

## Deployment and verification
- [ ] stop conditions declared
- [ ] canary/limited scope declared for R01/R02 as applicable
- [ ] smoke tests prepared
- [ ] rollback target known
- [ ] deployment evidence destination prepared

Unchecked mandatory items mean NOT READY. `VERIFIED` repository state alone never satisfies this checklist.

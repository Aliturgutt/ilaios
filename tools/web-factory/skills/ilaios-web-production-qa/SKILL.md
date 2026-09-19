---
name: ilaios-web-production-qa
description: Certify Web Factory production readiness only from exact-artifact deployment and live user-flow evidence, independently of any single hosting provider.
---
# ILAIOS Web Production QA
Status: IMPLEMENTED
Owner: ILAIOS

## Purpose
Prevent false production-ready claims by requiring exact deployment and live-flow evidence after implementation and validation gates pass.

## Contract
1. Require an immutable source/artifact identity and prove which deployment serves it.
2. Verify the intended production domain/alias resolves to that deployment where external production certification is requested.
3. Exercise critical routes, navigation, CTA/form paths, required locales and representative desktop/mobile viewports.
4. Record runtime errors, broken assets, redirects, auth boundaries and externally observable regressions.
5. Hosting-specific APIs are optional adapters; Vercel is not part of the native contract.
6. Build PASS, CI PASS or deployment creation alone cannot satisfy production certification.
7. Missing live evidence means NOT VERIFIED, not assumed PASS.

## Evidence
Production QA output must include artifact/SHA identity, deployment identity, domain checked, timestamp, tested flows, failures and final verdict. Production verdict is fail-closed.

---
name: ilaios-web-validation
description: Run deterministic, provider-independent Web Factory correctness gates over routes, links, forms, locale parity, assets, metadata, responsive output, security-sensitive boundaries, and artifact integrity.
---
# ILAIOS Web Validation
Status: IMPLEMENTED
Owner: ILAIOS

## Purpose
Separate implementation from proof by validating the generated artifact against explicit acceptance criteria.

## Contract
1. Validate required routes/pages, internal links, navigation and critical CTA destinations.
2. Validate asset references, metadata, canonical/locale declarations where required, and deterministic artifact integrity.
3. Validate responsive output against the required viewport matrix and locale parity contract.
4. Validate forms and interactive flows without bypassing auth, policy, approval or tenant boundaries.
5. Reject stale, missing, contradictory or wrong-artifact evidence.
6. Distinguish source checks, build checks, runtime checks and external production checks.
7. Never promote TESTED to VERIFIED or DEPLOYED without matching evidence.

## Evidence
Return explicit PASS/FAIL per gate with artifact identity, base SHA when applicable, observed failures and evidence references.

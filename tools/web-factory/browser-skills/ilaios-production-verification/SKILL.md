---
name: ilaios-production-verification
description: Capture bounded HTTPS browser evidence for production targets as an input to ILAIOS Web Production QA, without self-certifying deployment or release state.
---
# ILAIOS Production Verification
Status: IMPLEMENTED
Owner: ILAIOS

## Purpose
Supply live read-only HTTPS browser observations to the existing `ilaios-web-production-qa` certification stage.

## Contract
The target origin must be explicitly authorized and HTTPS. Execution follows BrowserQA -> Tool Gateway -> persisted work -> policy/budget -> Approval when required -> egress-enforced browser tool -> observed URL/artifact evidence -> Audit.

## Evidence semantics
Browser evidence can prove only that an allowed HTTPS target was reached and that declared observable criteria were present at execution time. It cannot by itself prove deployment ID/commit SHA linkage, CI success, backend/provider correctness, security properties not exercised, release approval, `PRODUCTION`, `VERIFIED` or `DONE`.

Redirects or browser observations outside policy fail the result. Real production certification still requires the canonical deployment/runtime/repository/CI evidence chain consumed by `ilaios-web-production-qa`.

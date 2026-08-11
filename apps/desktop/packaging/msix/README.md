# ILAIOS Desktop — Windows distribution packaging

This directory defines the deterministic packaging boundary for ILAIOS Desktop.

## Release model

1. GitHub Actions builds the already validated Windows release binary.
2. Packaging creates an MSIX/AppX-compatible package only from the validated Desktop output and canonical ILAIOS branding.
3. Signing is performed only when a trusted signing identity is explicitly provisioned. Private keys, certificate passwords, tokens, Partner Center credentials, and sensitive certificate material MUST NOT be committed to this repository.
4. Unsigned packages are CI artifacts only and MUST NOT be represented as trusted public releases.
5. Microsoft Store submission is a separate externally authenticated step and requires the publisher/Partner Center identity to exist and be approved.

## Authority and scope

Packaging does not alter the Desktop security architecture or move authorization, policy, tenant, governance, or execution authority into the client.

Website, Vercel, DNS, AWS, and unrelated repository areas are outside this packaging scope.

## Human/external blockers

Public signed distribution requires a code-signing identity/certificate or Microsoft Store signing path. Store publication requires an approved Microsoft Partner Center developer account, application identity/reservation, required listing metadata, declarations, and any mandatory account/payment verification.

CI may prepare and validate all deterministic inputs before those credentials are supplied, but it must fail closed rather than fabricate signing or Store approval.
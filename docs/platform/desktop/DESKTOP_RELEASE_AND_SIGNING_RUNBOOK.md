# Desktop Release and Signing Runbook

Status: CONTROLLED

## Scope

Windows Desktop packaging, Microsoft Store MSIX release, optional non-Store signing, certification evidence, publication and rollback for ILAIOS Desktop.

## Distribution modes

ILAIOS Desktop has two distinct production distribution paths. They must not be mixed.

### A. Microsoft Store MSIX — canonical public Windows distribution

For an MSIX submitted through Microsoft Store, ILAIOS does **not** require a repository-owned production code-signing certificate. The Store validates the submission and re-signs the package as part of certification. No PFX, certificate password, Azure signing credential or private key may be invented merely to satisfy the Store path.

The Store package manifest must still use the exact Partner Center product identity values. `Identity Name`, `Publisher` and the four-part package version must match the Partner Center product configuration.

### B. Direct / sideload / non-Store distribution

A package distributed outside Microsoft Store must follow the applicable trusted code-signing requirements for that distribution channel. Production signing material is RESTRICTED and must be held only in an approved signing service or secret facility. This path is independent from the Microsoft Store MSIX path.

## Build

Build from one clean, identified exact `master` SHA using locked dependencies and the supported Flutter/Windows toolchain. The release candidate must not be built from a moving branch, an unmerged PR head or an uncommitted local workspace.

Required source qualification includes the repository-owned Required CI Gate, Desktop CI/Windows release validation, relevant finished-product E2E checks and MSIX packaging/inspection checks for the same source SHA.

## Partner Center prerequisites

Before a Store release candidate can be produced with production identity, all of the following external facts must be available:

- Microsoft Store developer account status is active and publishing-enabled.
- The product name has been reserved in Partner Center.
- Partner Center `Package/Identity/Name` is known.
- Partner Center `Package/Identity/Publisher` is known.
- The next allowed four-part package version is known.

These values are external authority. Do not guess them and do not reuse the CI placeholders `ILAIOS.Desktop.CI` or `CN=ILAIOS-CI-UNSIGNED`.

## Microsoft Store production identity

Partner Center product identity captured on 2026-08-20:

- Product name: `ILAIOS`
- Product type: `MSIX or PWA app`
- `Package/Identity/Name`: `ILAIOS.ILAIOS`
- `Package/Identity/Publisher`: `CN=3BC70952-5109-4720-9A71-8B812EBCB255`
- `Package/Properties/PublisherDisplayName`: `ILAIOS`
- Package Family Name (PFN): `ILAIOS.ILAIOS_h6qnrfjyv0cv4`
- Store ID: `9P7787G6ZC5G`
- Microsoft Store product URL: `https://apps.microsoft.com/detail/9P7787G6ZC5G`
- Store protocol link: `ms-windows-store://pdp/?productid=9P7787G6ZC5G`

These are Store identity/configuration values, not secrets. Never place private signing keys, certificate passwords, access tokens, client secrets or other credentials in this document or in repository plaintext.

## Store release-candidate packaging

The controlled Store packaging entry point is:

```powershell
./tool/build_store_msix.ps1 `
  -IdentityName '<PARTNER_CENTER_IDENTITY_NAME>' `
  -Publisher '<PARTNER_CENTER_PUBLISHER>' `
  -Version '<A.B.C.D>'
```

The script fails closed if CI placeholder identity values are supplied, builds through the canonical MSIX builder, unpacks the result, verifies manifest identity/version equality and records SHA-256 release evidence.

The GitHub workflow `.github/workflows/desktop-store-release-candidate.yml` is the remote release-candidate gate. It is manual-only and requires:

- dispatch from `master`,
- an explicit expected `master` SHA,
- exact Partner Center identity and publisher values,
- an explicit four-part package version.

The workflow aborts if `master` moves after approval or if the supplied SHA/identity values are inconsistent.

## Microsoft Store signing model

The Store release candidate is intentionally recorded as `signed_before_submission=false`. This is not a production defect for the Microsoft Store MSIX path. Microsoft Store performs the trusted signing/re-signing step after certification.

Do not add a private signing certificate to GitHub solely for Microsoft Store MSIX submission.

## Validation before submission

On one exact source SHA, verify at minimum:

- Required CI Gate: PASS.
- Flutter static analysis: PASS.
- Flutter tests: PASS.
- Windows release build: PASS.
- Desktop Windows Gate: PASS where applicable to the changed scope.
- MSIX packaging: PASS.
- MSIX unpack/manifest inspection: PASS.
- Store manifest Identity Name/Publisher/Version exactly match Partner Center.
- Store package SHA-256 is recorded.
- Exact-master Windows launch: PASS.
- English/Turkish UI QA: PASS.
- 100%/125%/150% Windows scaling QA: PASS.
- Existing configured authentication regression: PASS.
- No fabricated runtime telemetry or evidence.

## Store submission

Create or open the Partner Center product submission, complete pricing/availability, properties, age ratings, package upload, Store listings and submission options, then submit for certification.

Store submission is an external production-impacting action. Preserve:

- exact source SHA,
- Store release-candidate package SHA-256,
- package version,
- Partner Center Identity Name and Publisher,
- submission ID,
- certification result,
- published Store version/link when available.

Store acceptance proves Microsoft Store publication for that package. It does not by itself prove backend production readiness.

## Post-certification verification

After certification and publication:

1. Install ILAIOS Desktop from the public/flighted Microsoft Store listing on a clean supported Windows environment.
2. Confirm the installed Store package is trusted and launches normally.
3. Verify authentication and control-plane connectivity.
4. Verify update behavior from the Store channel.
5. Re-run the critical Web/Video/Software execution smoke paths appropriate for the release.
6. Record Store version, installation evidence and release SHA linkage.

Only after these checks may the Store distribution state be reported as `DEPLOYED / PRODUCTION`.

## Rollback

Use Microsoft Store flight/availability controls where available or publish a corrected higher package version according to platform constraints. Never reuse a published package version for different bytes.

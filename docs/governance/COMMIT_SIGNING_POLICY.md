# ILAIOS Commit and Tag Signing Policy

## Decision

Existing unsigned history is not rewritten solely to add signatures. Signing is a forward-looking integrity control.

## Policy

- Release tags SHOULD be cryptographically signed when the maintainer signing identity is available.
- Commits that directly authorize or record production-sensitive release/security changes SHOULD be signed when supported by the maintainer environment.
- Automation identities must use GitHub-native verified identity or an explicitly governed signing mechanism; private signing keys must never be committed to the repository.
- Missing local signing credentials must fail closed for workflows that explicitly require signing, rather than silently substituting an unsigned artifact.
- Historical unsigned commits remain valid repository history but do not constitute cryptographic signer evidence.

## Enforcement boundary

Repository-side documentation and CI may verify signatures that exist, but configuring a maintainer's private GPG/SSH signing key is a credential-bound owner action. Branch/ruleset enforcement must only be enabled after the actual signing path is proven, so normal governed maintenance is not accidentally locked out.

## Release evidence

When signing is required for a release, record the tag/commit identity and GitHub verification result in the release evidence. Do not claim a signature where GitHub or the underlying signing tool does not verify it.

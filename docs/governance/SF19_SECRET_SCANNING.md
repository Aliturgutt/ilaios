# SF-19 Secret Scanning

SF-19 adds a deterministic, fail-closed secret scanning gate for Software Factory changesets.

## Scope

- CI scope: `REVIEWED_CHANGESET` added lines between exact base/head commit SHAs.
- Pre-commit scope: `STAGED_CHANGESET` added lines.
- Existing Security Factory secret detectors are reused for generic repository secret classes.
- Software Factory adds bounded high-confidence provider-token and high-entropy credential-assignment policy.
- Detected secret values are never emitted into evidence or CI logs.

## Authority boundary

SF-19 does not grant acceptance, promotion, deployment, publication, production, or repository-mutation authority. A passing secret scan proves only that the reviewed/staged added lines did not match the configured blocking secret policies.

It does not claim complete historical repository scanning, external secret-store validation, credential rotation, or proof that no unknown secret format exists.

# RELEASE.R00 Promotion Eligibility

The independent eligibility check passed without deployment. The authoritative
machine-readable record is `infra/release/promotion_eligibility.yaml`.

Release state remains `NOT_DEPLOYED`. Feature exposure defaults off, canary
access is allowlist-only, health prerequisites are mandatory, and rollback
requires both an immutable prior revision and the PLATFORM.P20 drill evidence.

Any transition to canary is outside RELEASE.R00 and requires explicit human
release-promotion approval under RELEASE.R01.

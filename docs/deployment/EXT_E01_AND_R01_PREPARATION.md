# EXT.E01 and RELEASE.R01 Preparation

This package inventories the safe work that can be completed before a provider,
account, region, domain, credentials, and accountable owners exist. It performs
no deployment and does not change `ReleaseState.NOT_DEPLOYED`.

## Prepared contracts

- `infra/deployment/ext-e01-prerequisites.yaml` records provider, platform,
  capability, ownership, runtime-gap, and human-decision inputs.
- `infra/deployment/dns-tls-template.yaml` records domain, DNS, certificate,
  renewal, and validation inputs without inventing values.
- `infra/deployment/secrets-inventory.yaml` records secret references and
  lifecycle controls; it contains no credentials.
- `infra/release/r01_canary_prerequisites.yaml` is a fail-closed checklist for
  the future, explicitly approved canary promotion.

## Vendor-neutral implementation direction

Prefer established portable components where the selected deployment profile
supports them: OpenTofu for infrastructure as code, OCI images, Kubernetes with
Kustomize for workload declarations, Argo CD or Flux for GitOps, External
Secrets Operator for reference-based secret delivery, and cert-manager for TLS
automation. Provider-specific modules and manifests must wait for architecture,
provider, region, and account decisions.

The repository currently supplies domain/service contracts rather than a
deployable network service. A production composition root, process command,
container build, HTTP liveness/readiness endpoints, dependency adapters,
capacity baseline, and migration/rollback mechanics must be implemented and
tested before provider-specific deployment manifests would be truthful.

## Promotion boundary

Preparation is not promotion. RELEASE.R01 remains prohibited until its explicit
human approval exists and every infrastructure, exposure, operations, and
security prerequisite in the canary checklist has independently verifiable
evidence. RELEASE.R02 and RELEASE.R03 remain out of scope.

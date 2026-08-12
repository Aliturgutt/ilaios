# Backup, Restore and Disaster Recovery

Status: CONTROLLED

## Scope
Covers production state that cannot be reconstructed safely from source, immutable artifacts and external systems of record.

## Objectives
Until production topology and measured recovery tests establish stronger values, use planning objectives of RPO <=24 hours and RTO <=8 hours for non-critical v1 state. Any stricter product commitment requires a dedicated measured service objective. Critical identity/signing/secret systems follow provider recovery controls and separate key procedures.

## Backups
Backups must be encrypted, access-controlled, environment-scoped, monitored for failure, and protected from routine application deletion where feasible. Backup schedules and retention must align with privacy/data-retention rules.

## Restore tests
A backup is not VERIFIED until restore is tested. At least quarterly while production state exists, restore representative data into an isolated environment, validate integrity/application readability, record duration and gaps, and destroy test data according to policy.

## Disaster recovery
Declare trigger, incident owner, target environment, dependency order, DNS/traffic procedure where applicable, data restore point, credential/key dependencies, validation checks, rollback/forward path, and communication plan.

## Evidence
Retain backup job IDs, restore drill results, integrity checks, achieved RPO/RTO, exceptions and corrective actions. Production readiness fails closed when required backups or restore evidence are missing.

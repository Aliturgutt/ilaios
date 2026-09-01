# Key Management and Cryptography Operations

Status: CONTROLLED

## Principles
Use managed KMS/HSM or approved secret-management facilities for production key material. Application repositories store references and configuration, never live private keys or long-lived secrets.

## Separation
Encryption keys, signing keys, API credentials and application secrets are distinct security objects with separate permissions. Production signing identities must not be routinely available to development workloads.

## Cryptography
Use current platform/provider cryptographic primitives and TLS configurations; do not invent proprietary cryptography. Deprecated hashes/ciphers are prohibited for security purposes except where required to verify legacy artifacts during migration.

## Rotation
Each key class requires an owner, creation date, purpose, environment, cryptoperiod/rotation trigger, revocation procedure and dependency map. Rotation must be tested for overlap/compatibility where zero-downtime is required.

## Emergency rotation
Suspected compromise triggers immediate containment: disable/revoke where safe, issue replacement, update dependents through governed deployment, verify old material is unusable, and preserve non-secret evidence.

## Access and evidence
Least privilege, MFA/phishing-resistant controls for privileged operations where supported, auditable key-use events, and no plaintext export unless explicitly required and approved. Record key IDs/versions and operation results, never secret values.

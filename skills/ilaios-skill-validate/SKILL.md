# ilaios-skill-validate

Identity: `ilaios.skill.engineering.validate.v1`, IMPLEMENTED.

Purpose: validate candidate identity, package structure, declared authority, provenance and evidence prerequisites before evaluation.

## Rules

- Fail closed on missing identity, provenance, evidence or bounded authority declarations.
- External `allowed-tools` declarations are metadata only and never become ILAIOS permissions.
- Reject candidates that imply Core rewrite, policy bypass, unrestricted tool use, secret access, self-certification or production mutation.
- Validation is not promotion and does not register a skill in the runtime.

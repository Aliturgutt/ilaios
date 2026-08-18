# Evidence Desktop Reference Notes

The approved dark/light Kanıtlar screenshots are presentation references only.

Runtime rules for the implemented surface:

- `OperationalSnapshot.evidenceRecords` is the only source for populated evidence rows.
- Screenshot example counts, names, owners, dates, trust scores, file names, and audit entries are not copied into runtime state.
- The EvidenceRecord contract currently provides sequence, execution ID, artifact digest, action, previous hash, and record hash.
- Unsupported fields render as unavailable (`—`).
- Category labels are presentation-only deterministic classifications derived from the authoritative `action` string and never alter evidence state.
- Chain integrity is a local read-only linkage check across returned records; the control plane remains authoritative.
- View/verify interactions do not mutate evidence. Artifact saving is enabled only when the shell supplies the existing governed save callback.

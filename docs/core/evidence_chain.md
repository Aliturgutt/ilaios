# Evidence Chain Specification

> Historical provenance specification. Its active implementation belongs to ILAIOS; references to Hermes below preserve origin and do not identify a separate active product.

## 1. Purpose and Scope
Define a deterministic, append‑only record chain that captures immutable execution evidence for Hermes Enterprise OS core components. The chain links each evidence record to its predecessor via cryptographic hashes, providing verifiable ordering and integrity without external storage.

## 2. Implementation File
- **Code location:** `src/core/evidence_chain.py`
- **Documentation:** `docs/core/evidence_chain.md`

## 3. Public Interface
```python
from datetime import datetime
from hashlib import sha256
from typing import Optional

class EvidenceRecord:
    timestamp: datetime
    source: str
    data_hash: str
    prev_hash: Optional[str]
    chain_hash: str

class EvidenceChain:
    def __init__(self) -> None: ...
    def add_record(self, record: EvidenceRecord) -> None: ...
    def get_root_hash(self) -> str: ...
    def verify_integrity(self) -> bool: ...
```

## 4. Evidence Record Data Model
| Field        | Type                     | Description |
|--------------|--------------------------|-------------|
| `timestamp`  | `datetime` (UTC, ISO‑8601) | Moment of record creation |
| `source`     | `str`                     | Identifier of the emitting component (e.g., "immutable_context") |
| `data_hash`  | `str`                     | SHA‑256 hash of the payload being recorded |
| `prev_hash`  | `Optional[str]`           | Hash of the previous record; `None` for the genesis record |
| `chain_hash` | `str`                     | SHA‑256 hash of the concatenated fields `timestamp|source|data_hash|prev_hash` |

## 5. Immutability Rules
- Records are **append‑only**; once added they cannot be modified.
- All fields are immutable after instantiation.
- The chain may only grow forward.

## 6. Ordering and Chain‑Linking
- Each new `EvidenceRecord` must reference the `chain_hash` of the current tip as its `prev_hash`.
- The first record (genesis) has `prev_hash=None`.
- Validation ensures each link correctly points to its predecessor.

## 7. Integrity / Hash Requirements
- `chain_hash` = `sha256(timestamp.isoformat() + source + data_hash + prev_hash or "")`
- The `chain_hash` field must match the computed hash; mismatch invalidates the chain.

## 8. Validation and Failure Behavior
- `add_record` validates cryptographic linkage and raises `EvidenceChainValidationError` if any rule is violated.
- `verify_integrity` walks the chain from tip to genesis and recomputes hashes, returning `True` only if all links match.

## 9. Dependencies
- Relies on `ExecutionContext` for obtaining the execution context when generating records.
- May optionally use `OpenRouterAgent` for structured logging of chain events (non‑critical).
- No external database or filesystem persistence is required; the chain lives in memory.

## 10. Prohibited Responsibilities
- Direct file I/O beyond in‑memory storage of the chain.
- Network calls or external service interactions.
- Mutation of existing records.
- Generation of evidence for non‑core components.

## 11. Required Unit‑Test Cases
1. **Valid addition** – Adding a correctly linked record updates the chain tip and passes integrity check.
2. **Link mismatch** – Adding a record with an incorrect `prev_hash` raises `EvidenceChainValidationError`.
3. **Integrity verification** – `verify_integrity` returns `True` for a valid chain and `False` after tampering.
4. **Genesis record** – First record is accepted when `prev_hash=None`.

## 12. Acceptance Criteria
- `docs/core/evidence_chain.md` exists and is syntactically valid.
- The specification accurately reflects the intended public interface and data model.
- `PROJECT_STATUS.md` is updated to indicate “Evidence Chain specification: COMPLETED (implementation pending)”.
- No documentation lint errors are reported (`pre‑commit` hooks pass).

## 13. Notes
- The design intentionally avoids external dependencies to stay within the current Hermes architecture constraints.
- Future implementations may plug this chain into audit or policy engines, but such integration is outside the scope of this spec.

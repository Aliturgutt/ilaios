"""Isolated Software Factory that can only propose bounded changes."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import PurePosixPath


class SoftwareFactoryError(PermissionError):
    """Raised when a proposed self-change exceeds its isolated boundary."""


@dataclass(frozen=True, slots=True)
class ChangeProposal:
    proposal_id: str
    target_path: str
    content_hash: str
    requires_human_approval: bool = True
    production_applied: bool = False


class IsolatedSoftwareFactory:
    """Produces reviewable proposals and has no production-write capability."""

    def __init__(self, allowed_roots: frozenset[str]) -> None:
        self._allowed_roots = allowed_roots

    def propose(self, target_path: str, content: bytes) -> ChangeProposal:
        path = PurePosixPath(target_path)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise SoftwareFactoryError("target path escapes isolation")
        if path.parts[0] not in self._allowed_roots:
            raise SoftwareFactoryError("target path is outside the bounded allowlist")
        digest = hashlib.sha256(content).hexdigest()
        return ChangeProposal(f"change-{digest[:16]}", str(path), digest)

    def apply_to_production(self, proposal: ChangeProposal) -> None:
        del proposal
        raise SoftwareFactoryError("autonomous direct production mutation is forbidden")

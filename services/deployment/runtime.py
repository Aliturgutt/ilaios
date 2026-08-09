"""Production composition command using provider-neutral local adapters."""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

from services.control_plane.server import main as control_plane_main


def main(argv: Sequence[str] | None = None) -> int:
    if argv:
        raise ValueError("production runtime accepts configuration through environment")
    state_root_raw = os.environ.get("ILAIOS_STATE_ROOT", "")
    ready_file_raw = os.environ.get("ILAIOS_READY_FILE", "")
    if not state_root_raw or not ready_file_raw:
        raise ValueError("ILAIOS_STATE_ROOT and ILAIOS_READY_FILE are required")
    state_root = Path(state_root_raw)
    if not state_root.is_absolute():
        raise ValueError("ILAIOS_STATE_ROOT must be absolute")
    state_root.mkdir(parents=True, exist_ok=True)
    return control_plane_main(
        (
            "--database",
            str(state_root / "control.sqlite3"),
            "--host",
            os.environ.get("ILAIOS_HOST", "127.0.0.1"),
            "--port",
            os.environ.get("ILAIOS_PORT", "0"),
            "--ready-file",
            ready_file_raw,
            "--evidence-root",
            str(state_root / "evidence"),
            "--governance-database",
            str(state_root / "governance.sqlite3"),
            "--hard-cap-minor",
            os.environ.get("ILAIOS_HARD_CAP_MINOR", "100"),
            "--video-root",
            str(state_root / "video"),
            "--product-proof-database",
            str(state_root / "product-proof.sqlite3"),
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())

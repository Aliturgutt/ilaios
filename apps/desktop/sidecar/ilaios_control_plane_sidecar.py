"""Packaged Windows entrypoint for the local ILAIOS control plane.

The Desktop launcher supplies a fresh bearer token through the process
environment. This entrypoint derives all durable local paths from one explicit
per-user data root and delegates authority to the canonical control-plane
server; it does not implement a second runtime.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from services.control_plane.server import main as control_plane_main


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--ready-file", type=Path, required=True)
    arguments = parser.parse_args(argv)

    root = arguments.data_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    arguments.ready_file.parent.mkdir(parents=True, exist_ok=True)

    return control_plane_main(
        (
            "--database",
            str(root / "control-plane.sqlite3"),
            "--host",
            "127.0.0.1",
            "--port",
            "0",
            "--ready-file",
            str(arguments.ready_file),
            "--evidence-root",
            str(root / "evidence"),
            "--governance-database",
            str(root / "governance.sqlite3"),
            "--video-root",
            str(root / "video"),
            "--product-proof-database",
            str(root / "product-proof.sqlite3"),
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())

"""Reference-aware packaged Windows composition root for ILAIOS Desktop."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

import ilaios_control_plane_sidecar_core as _core
from services.integrations.reference_video_runtime import (
    ReferenceAwareProviderBackedDesktopVideoRuntime,
)
from services.integrations.reference_web_product_runtime import (
    ReferenceAwareRecoverableWebProductRuntime,
)
from services.reference_asset_desktop import ReferenceAwareDesktopIdentityHTTPServer
from services.reference_assets import configure_reference_asset_store


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    # Preserve the canonical CLI help/import smoke contract. Help must not need a
    # writable data root or initialize durable reference storage.
    if "--help" in arguments or "-h" in arguments:
        return _core.main(argv)

    root = _data_root(arguments)
    configure_reference_asset_store(
        root / "reference-assets.sqlite3",
        root / "reference-assets" / "objects",
    )

    # Extend the existing single composition root in place. No second control
    # plane, coordinator, scheduler, or governance authority is introduced.
    _core.DesktopIdentityHTTPServer = ReferenceAwareDesktopIdentityHTTPServer
    _core.RecoverableWebProductRuntime = ReferenceAwareRecoverableWebProductRuntime
    _core.ProviderBackedDesktopVideoRuntime = ReferenceAwareProviderBackedDesktopVideoRuntime
    return _core.main(argv)


def _data_root(arguments: Sequence[str]) -> Path:
    try:
        index = arguments.index("--data-root")
        raw = arguments[index + 1]
    except (ValueError, IndexError) as error:
        raise SystemExit("--data-root is required") from error
    if not raw.strip():
        raise SystemExit("--data-root is required")
    return Path(raw).resolve()


if __name__ == "__main__":
    raise SystemExit(main())

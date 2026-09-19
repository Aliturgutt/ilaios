from __future__ import annotations

import struct

from apps.desktop.e2e.provider_video_native_reference_semantic_diagnostic_e2e import (
    _provider_valid_logo_png_bytes,
)


def test_native_reference_certification_logo_meets_seedance_reference_bounds() -> None:
    content = _provider_valid_logo_png_bytes()

    assert content.startswith(b"\x89PNG\r\n\x1a\n")
    width, height = struct.unpack(">II", content[16:24])

    assert 300 <= width <= 6000
    assert 300 <= height <= 6000
    assert 0.4 <= width / height <= 2.5

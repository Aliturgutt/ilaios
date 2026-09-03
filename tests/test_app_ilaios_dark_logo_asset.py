from __future__ import annotations

import struct
import zlib
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DARK_ASSET = _REPO_ROOT / "brand" / "assets" / "02-ilaios-primary-horizontal-dark-carbon.png"
_RUNTIME = _REPO_ROOT / "apps" / "web_app_runtime" / "login_server.py"


def _png_top_left_rgb(data: bytes) -> tuple[tuple[int, int], tuple[int, int, int]]:
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    offset = 8
    width = height = bit_depth = color_type = None
    idat = bytearray()
    while offset < len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + length]
        offset += 12 + length
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(
                ">IIBBBBB", payload
            )
            assert (compression, filtering, interlace) == (0, 0, 0)
        elif chunk_type == b"IDAT":
            idat.extend(payload)
        elif chunk_type == b"IEND":
            break

    assert (width, height, bit_depth, color_type) == (2400, 800, 8, 2)
    scanlines = zlib.decompress(bytes(idat))
    assert scanlines[0] in {0, 1, 2, 3, 4}
    return (width, height), tuple(scanlines[1:4])


def test_dark_logo_asset_canvas_starts_at_canonical_carbon() -> None:
    size, top_left = _png_top_left_rgb(_DARK_ASSET.read_bytes())
    assert size == (2400, 800)
    assert top_left == (10, 10, 10)


def test_login_runtime_uses_lossless_dark_asset_without_touching_light_asset() -> None:
    source = _RUNTIME.read_text(encoding="utf-8")
    assert '"13-ilaios-primary-horizontal-light.jpg"' in source
    assert '"02-ilaios-primary-horizontal-dark-carbon.png"' in source
    assert 'src="/login/brand-light.jpg"' in source
    assert 'src="/login/brand-dark.png"' in source
    assert 'if split.path == "/login/brand-dark.png":' in source
    assert 'return self._asset_response(_BRAND_DARK, "image/png")' in source

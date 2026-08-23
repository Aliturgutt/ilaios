from __future__ import annotations

import struct
import zlib

from apps.desktop.e2e.provider_video_native_reference_semantic_diagnostic_e2e import (
    _provider_quality_product_png_bytes,
)


def _decode_rgb_png(payload: bytes) -> tuple[int, int, bytes]:
    assert payload.startswith(b"\x89PNG\r\n\x1a\n")
    offset = 8
    width = height = 0
    compressed = bytearray()
    while offset < len(payload):
        length = struct.unpack(">I", payload[offset : offset + 4])[0]
        kind = payload[offset + 4 : offset + 8]
        chunk = payload[offset + 8 : offset + 8 + length]
        offset += 12 + length
        if kind == b"IHDR":
            width, height = struct.unpack(">II", chunk[:8])
        elif kind == b"IDAT":
            compressed.extend(chunk)
        elif kind == b"IEND":
            break
    raw = zlib.decompress(bytes(compressed))
    stride = width * 3
    rgb = bytearray()
    for row in range(height):
        start = row * (stride + 1)
        assert raw[start] == 0
        rgb.extend(raw[start + 1 : start + 1 + stride])
    return width, height, bytes(rgb)


def _pixel(rgb: bytes, width: int, x: int, y: int) -> tuple[int, int, int]:
    offset = (y * width + x) * 3
    return tuple(rgb[offset : offset + 3])  # type: ignore[return-value]


def test_provider_quality_product_reference_is_rich_and_provider_valid() -> None:
    width, height, rgb = _decode_rgb_png(_provider_quality_product_png_bytes())

    assert (width, height) == (640, 360)
    assert _pixel(rgb, width, 320, 180)[1] > 150  # cyan identity channel
    emblem = _pixel(rgb, width, 421, 132)
    assert emblem[0] > 200 and emblem[1] < 150 and emblem[2] < 90

    body_left = _pixel(rgb, width, 190, 180)
    body_center = _pixel(rgb, width, 260, 180)
    body_right = _pixel(rgb, width, 465, 180)
    assert body_left != body_center != body_right

    unique_colors = {
        tuple(rgb[index : index + 3]) for index in range(0, len(rgb), 3)
    }
    assert len(unique_colors) >= 100

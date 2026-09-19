from __future__ import annotations

from services.p0_live_certification import (
    _CERTIFICATION_INPUT_TOKEN_RESERVATION,
    _CERTIFICATION_OUTPUT_TOKEN_RESERVATION,
)


def test_p0_live_certification_token_reservations_remain_bounded() -> None:
    assert _CERTIFICATION_INPUT_TOKEN_RESERVATION == 4096
    assert _CERTIFICATION_OUTPUT_TOKEN_RESERVATION == 2048
    assert 0 < _CERTIFICATION_OUTPUT_TOKEN_RESERVATION <= 4096
    assert _CERTIFICATION_OUTPUT_TOKEN_RESERVATION < _CERTIFICATION_INPUT_TOKEN_RESERVATION

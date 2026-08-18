from __future__ import annotations

from pathlib import Path


def _adapter_source() -> str:
    root = Path(__file__).resolve().parents[1]
    return (root / "services" / "runtime" / "ai_provider_adapter.py").read_text(
        encoding="utf-8"
    )


def test_output_ceiling_failure_exposes_only_bounded_numeric_usage() -> None:
    source = _adapter_source()
    start = source.index("if response.output_tokens > max_output_tokens:")
    end = source.index("actual_cost = _cost(", start)
    block = source[start:end]

    assert "provider exceeded requested output-token ceiling:" in block
    assert "requested={max_output_tokens}" in block
    assert "observed={response.output_tokens}" in block
    assert "prompt" not in block
    assert "response.text" not in block
    assert "api_key" not in block


def test_input_ceiling_failure_exposes_only_bounded_numeric_usage() -> None:
    source = _adapter_source()
    start = source.index("if response.input_tokens > reserved_input_tokens:")
    end = source.index("if response.output_tokens > max_output_tokens:", start)
    block = source[start:end]

    assert "provider exceeded reserved input-token ceiling:" in block
    assert "requested={reserved_input_tokens}" in block
    assert "observed={response.input_tokens}" in block
    assert "prompt" not in block
    assert "response.text" not in block
    assert "api_key" not in block

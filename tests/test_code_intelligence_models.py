"""Tests for src.code_intelligence.models."""

from src.code_intelligence.models import Language, Symbol, SymbolType


def test_symbol_can_be_constructed() -> None:
    symbol = Symbol(
        symbol_id="sym-1",
        name="foo",
        symbol_type=SymbolType.FUNCTION,
        location="src/foo.py:1",
        language=Language.PYTHON,
    )
    assert symbol.id == "sym-1"
    assert symbol.name == "foo"
    assert symbol.type == SymbolType.FUNCTION
    assert symbol.location == "src/foo.py:1"
    assert symbol.language == Language.PYTHON


def test_symbol_references_default_to_empty_list() -> None:
    symbol = Symbol(
        symbol_id="sym-1",
        name="foo",
        symbol_type=SymbolType.FUNCTION,
        location="src/foo.py:1",
        language=Language.PYTHON,
    )
    assert symbol.references == []


def test_symbol_metadata_defaults_to_empty_dict() -> None:
    symbol = Symbol(
        symbol_id="sym-1",
        name="foo",
        symbol_type=SymbolType.FUNCTION,
        location="src/foo.py:1",
        language=Language.PYTHON,
    )
    assert symbol.metadata == {}


def test_symbol_instances_have_independent_collections() -> None:
    symbol_a = Symbol(
        symbol_id="sym-a",
        name="a",
        symbol_type=SymbolType.CLASS,
        location="src/a.py:1",
        language=Language.PYTHON,
    )
    symbol_b = Symbol(
        symbol_id="sym-b",
        name="b",
        symbol_type=SymbolType.CLASS,
        location="src/b.py:1",
        language=Language.PYTHON,
    )

    symbol_a.references.append("ref-1")
    symbol_a.metadata["key"] = "value"

    assert symbol_b.references == []
    assert symbol_b.metadata == {}
    assert symbol_a.references is not symbol_b.references
    assert symbol_a.metadata is not symbol_b.metadata

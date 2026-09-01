# mypy: disable-error-code=misc
"""Tests for deterministic code-intelligence models."""

from dataclasses import FrozenInstanceError

import pytest

from src.code_intelligence.models import (
    CodeEntity,
    Language,
    SourceLocation,
    Symbol,
    SymbolType,
)


def make_entity() -> CodeEntity:
    """Create a standard entity for test reuse."""

    return CodeEntity(
        entity_id="function:src/example.py:run",
        name="run",
        entity_type=SymbolType.FUNCTION,
        location=SourceLocation(
            path="src/example.py",
            line=10,
            column=4,
        ),
        language=Language.PYTHON,
    )


def test_source_location_can_be_constructed() -> None:
    location = SourceLocation(
        path="src/example.py",
        line=10,
        column=4,
    )

    assert location.path == "src/example.py"
    assert location.line == 10
    assert location.column == 4


def test_source_location_defaults_column_to_zero() -> None:
    location = SourceLocation(path="src/example.py", line=1)

    assert location.column == 0
    assert location.render() == "src/example.py:1:0"


@pytest.mark.parametrize("path", ["", " ", " src/example.py", "src/example.py "])
def test_source_location_rejects_invalid_path(path: str) -> None:
    with pytest.raises(ValueError):
        SourceLocation(path=path, line=1)


@pytest.mark.parametrize(
    ("line", "column"),
    [
        (0, 0),
        (-1, 0),
        (1, -1),
    ],
)
def test_source_location_rejects_invalid_coordinates(
    line: int,
    column: int,
) -> None:
    with pytest.raises(ValueError):
        SourceLocation(
            path="src/example.py",
            line=line,
            column=column,
        )


def test_code_entity_can_be_constructed() -> None:
    entity = make_entity()

    assert entity.entity_id == "function:src/example.py:run"
    assert entity.id == entity.entity_id
    assert entity.name == "run"
    assert entity.entity_type is SymbolType.FUNCTION
    assert entity.type is SymbolType.FUNCTION
    assert entity.language is Language.PYTHON
    assert entity.references == ()
    assert entity.metadata == {}


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("entity_id", ""),
        ("entity_id", " "),
        ("entity_id", " entity-1"),
        ("entity_id", "entity-1 "),
        ("name", ""),
        ("name", " "),
        ("name", " run"),
        ("name", "run "),
    ],
)
def test_code_entity_rejects_invalid_text_fields(
    field_name: str,
    value: str,
) -> None:
    values = {
        "entity_id": "entity-1",
        "name": "run",
    }
    values[field_name] = value

    with pytest.raises(ValueError):
        CodeEntity(
            entity_id=values["entity_id"],
            name=values["name"],
            entity_type=SymbolType.FUNCTION,
            location=SourceLocation("src/example.py", 1),
            language=Language.PYTHON,
        )


def test_code_entity_normalizes_references_to_tuple() -> None:
    entity = CodeEntity(
        entity_id="entity-1",
        name="run",
        entity_type=SymbolType.FUNCTION,
        location=SourceLocation("src/example.py", 1),
        language=Language.PYTHON,
        references=("entity-2", "entity-3"),
    )

    assert entity.references == ("entity-2", "entity-3")


def test_code_entity_rejects_duplicate_references() -> None:
    with pytest.raises(ValueError, match="duplicate reference"):
        CodeEntity(
            entity_id="entity-1",
            name="run",
            entity_type=SymbolType.FUNCTION,
            location=SourceLocation("src/example.py", 1),
            language=Language.PYTHON,
            references=("entity-2", "entity-2"),
        )


@pytest.mark.parametrize("reference", ["", " ", " entity-2", "entity-2 "])
def test_code_entity_rejects_invalid_references(reference: str) -> None:
    with pytest.raises(ValueError):
        CodeEntity(
            entity_id="entity-1",
            name="run",
            entity_type=SymbolType.FUNCTION,
            location=SourceLocation("src/example.py", 1),
            language=Language.PYTHON,
            references=(reference,),
        )


def test_code_entity_orders_metadata_deterministically() -> None:
    entity = CodeEntity(
        entity_id="entity-1",
        name="run",
        entity_type=SymbolType.FUNCTION,
        location=SourceLocation("src/example.py", 1),
        language=Language.PYTHON,
        metadata={
            "zeta": 2,
            "alpha": 1,
        },
    )

    assert tuple(entity.metadata.items()) == (
        ("alpha", 1),
        ("zeta", 2),
    )


def test_code_entity_metadata_is_read_only() -> None:
    entity = make_entity()

    with pytest.raises(TypeError):
        entity.metadata["key"] = "value"  # type: ignore[index]


def test_code_entity_is_immutable() -> None:
    entity = make_entity()

    with pytest.raises(FrozenInstanceError):
        entity.name = "changed"


def test_with_reference_returns_new_entity() -> None:
    entity = make_entity()

    updated = entity.with_reference("class:src/example.py:Runner")

    assert updated is not entity
    assert entity.references == ()
    assert updated.references == ("class:src/example.py:Runner",)


def test_with_existing_reference_returns_same_entity() -> None:
    entity = make_entity().with_reference("entity-2")

    assert entity.with_reference("entity-2") is entity


def test_with_metadata_returns_new_entity() -> None:
    entity = make_entity()

    updated = entity.with_metadata("complexity", 3)

    assert updated is not entity
    assert entity.metadata == {}
    assert updated.metadata == {"complexity": 3}


def test_equivalent_entities_are_equal_and_have_equal_hashes() -> None:
    entity_a = CodeEntity(
        entity_id="entity-1",
        name="run",
        entity_type=SymbolType.FUNCTION,
        location=SourceLocation("src/example.py", 1),
        language=Language.PYTHON,
        metadata={"zeta": 2, "alpha": 1},
    )
    entity_b = CodeEntity(
        entity_id="entity-1",
        name="run",
        entity_type=SymbolType.FUNCTION,
        location=SourceLocation("src/example.py", 1),
        language=Language.PYTHON,
        metadata={"alpha": 1, "zeta": 2},
    )

    assert entity_a == entity_b
    assert hash(entity_a) == hash(entity_b)


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
    assert symbol.type is SymbolType.FUNCTION
    assert symbol.location == "src/foo.py:1"
    assert symbol.language is Language.PYTHON


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

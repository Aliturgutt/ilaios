"""Deterministic data models for code intelligence."""

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from enum import Enum
from types import MappingProxyType
from typing import TypeAlias

MetadataValue: TypeAlias = str | int | float | bool | None


class Language(Enum):
    """Programming languages supported by code intelligence."""

    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    GO = "go"
    RUST = "rust"
    JAVA = "java"
    DART = "dart"


class Certainty(str, Enum):
    """Strength of evidence behind an intelligence assertion."""

    KNOWN = "known"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class FileKind(str, Enum):
    SOURCE = "source"
    TEST = "test"
    CONFIGURATION = "configuration"
    MANIFEST = "manifest"
    GENERATED = "generated"


class SymbolType(Enum):
    """Supported code-entity classifications."""

    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    IMPORT = "import"
    API_ROUTE = "api_route"
    SCHEMA = "schema"
    EXPORT = "export"


@dataclass(frozen=True, slots=True)
class SourceLocation:
    """Immutable source-code location."""

    path: str
    line: int
    column: int = 0

    def __post_init__(self) -> None:
        if not self.path or not self.path.strip():
            raise ValueError("path must not be empty")
        if self.path != self.path.strip():
            raise ValueError("path must not contain surrounding whitespace")
        if self.line < 1:
            raise ValueError("line must be greater than or equal to 1")
        if self.column < 0:
            raise ValueError("column must be greater than or equal to 0")

    def render(self) -> str:
        """Return a deterministic textual representation."""

        return f"{self.path}:{self.line}:{self.column}"


@dataclass(frozen=True, slots=True)
class CodeEntity:
    """Immutable and deterministic representation of a code entity."""

    entity_id: str
    name: str
    entity_type: SymbolType
    location: SourceLocation
    language: Language
    references: tuple[str, ...] = ()
    metadata: Mapping[str, MetadataValue] = field(
        default_factory=dict,
        repr=False,
    )

    def __post_init__(self) -> None:
        self._validate_text("entity_id", self.entity_id)
        self._validate_text("name", self.name)

        normalized_references = tuple(self.references)
        seen_references: set[str] = set()

        for reference in normalized_references:
            self._validate_text("reference", reference)
            if reference in seen_references:
                raise ValueError(f"duplicate reference: {reference}")
            seen_references.add(reference)

        normalized_metadata: dict[str, MetadataValue] = {}
        for key, value in self.metadata.items():
            self._validate_text("metadata key", key)
            normalized_metadata[key] = value

        ordered_metadata = dict(sorted(normalized_metadata.items()))

        object.__setattr__(self, "references", normalized_references)
        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(ordered_metadata),
        )

    @staticmethod
    def _validate_text(field_name: str, value: str) -> None:
        if not value or not value.strip():
            raise ValueError(f"{field_name} must not be empty")
        if value != value.strip():
            raise ValueError(
                f"{field_name} must not contain surrounding whitespace"
            )

    @property
    def id(self) -> str:
        """Return the stable entity identifier."""

        return self.entity_id

    @property
    def type(self) -> SymbolType:
        """Return the entity classification."""

        return self.entity_type

    def with_reference(self, reference: str) -> "CodeEntity":
        """Return a new entity containing one additional reference."""

        self._validate_text("reference", reference)

        if reference in self.references:
            return self

        return replace(
            self,
            references=(*self.references, reference),
        )

    def with_metadata(
        self,
        key: str,
        value: MetadataValue,
    ) -> "CodeEntity":
        """Return a new entity containing an updated metadata entry."""

        self._validate_text("metadata key", key)

        updated_metadata = dict(self.metadata)
        updated_metadata[key] = value

        return replace(self, metadata=updated_metadata)

    def __hash__(self) -> int:
        """Return a stable hash based on deterministic entity state."""

        return hash(
            (
                self.entity_id,
                self.name,
                self.entity_type,
                self.location,
                self.language,
                self.references,
                tuple(self.metadata.items()),
            )
        )


class Symbol:
    """Backward-compatible mutable code symbol.

    New code should use ``CodeEntity``. This model remains available to avoid
    breaking the existing repository contract.
    """

    def __init__(
        self,
        symbol_id: str,
        name: str,
        symbol_type: SymbolType,
        location: str,
        language: Language,
    ) -> None:
        self.id = symbol_id
        self.name = name
        self.type = symbol_type
        self.location = location
        self.language = language
        self.references: list[str] = []
        self.metadata: dict[str, MetadataValue] = {}


@dataclass(frozen=True, slots=True)
class SourceFileRecord:
    path: str
    language: Language | None
    kind: FileKind
    module: str | None
    package: str | None
    generated: bool
    certainty: Certainty


@dataclass(frozen=True, slots=True)
class SymbolRecord:
    symbol_id: str
    name: str
    qualified_name: str
    symbol_type: SymbolType
    location: SourceLocation
    language: Language
    public: bool
    parent_symbol_id: str | None = None
    bases: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
    certainty: Certainty = Certainty.KNOWN


@dataclass(frozen=True, slots=True)
class DependencyEdge:
    source: str
    target: str
    relationship: str
    certainty: Certainty


@dataclass(frozen=True, slots=True)
class TestMapping:
    test_file: str
    source_files: tuple[str, ...]
    certainty: Certainty
    rationale: str


@dataclass(frozen=True, slots=True)
class RepositorySnapshot:
    root: str
    revision: str
    files: tuple[SourceFileRecord, ...]
    symbols: tuple[SymbolRecord, ...]
    dependencies: tuple[DependencyEdge, ...]
    test_mappings: tuple[TestMapping, ...]
    api_routes: tuple[str, ...]
    schema_entities: tuple[str, ...]
    manifests: tuple[str, ...]
    configurations: tuple[str, ...]
    unknowns: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ImpactAnalysis:
    changed_files: tuple[str, ...]
    changed_symbols: tuple[str, ...]
    affected_files: tuple[str, ...]
    affected_packages: tuple[str, ...]
    affected_apis: tuple[str, ...]
    affected_tests: tuple[str, ...]
    regression_surface: tuple[str, ...]
    confidence: Certainty
    unknowns: tuple[str, ...]
    recommended_validation_profile: tuple[str, ...]

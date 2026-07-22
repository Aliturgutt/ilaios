from enum import Enum
from typing import Any, Dict, List


class Language(Enum):
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    GO = "go"
    RUST = "rust"
    JAVA = "java"


class SymbolType(Enum):
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    IMPORT = "import"


class Symbol:
    """Represents a code symbol."""

    def __init__(self,
                 symbol_id: str,
                 name: str,
                 symbol_type: SymbolType,
                 location: str,
                 language: Language):
        self.id = symbol_id
        self.name = name
        self.type = symbol_type
        self.location = location
        self.language = language
        self.references: List[str] = []
        self.metadata: Dict[str, Any] = {}

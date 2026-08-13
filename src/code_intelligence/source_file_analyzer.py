"""Deterministic source-file loading for code intelligence."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import ClassVar

from src.code_intelligence.models import Language

DEFAULT_MAX_FILE_SIZE_BYTES = 1_048_576


class SourceFileAnalyzerError(Exception):
    """Base error raised by the source-file analyzer."""


class SourceFileNotFoundError(SourceFileAnalyzerError):
    """Raised when the requested source file does not exist."""


class SourceFileOutsideRootError(SourceFileAnalyzerError):
    """Raised when a source file is outside the configured root."""


class UnsupportedSourceLanguageError(SourceFileAnalyzerError):
    """Raised when a source-file extension is unsupported."""


class SourceFileTooLargeError(SourceFileAnalyzerError):
    """Raised when a source file exceeds the configured size limit."""


class SourceFileDecodeError(SourceFileAnalyzerError):
    """Raised when a source file is not valid UTF-8 text."""


class BinarySourceFileError(SourceFileAnalyzerError):
    """Raised when a source file contains binary null bytes."""


@dataclass(frozen=True, slots=True)
class SourceFile:
    """Immutable result of deterministic source-file analysis."""

    path: str
    language: Language
    content: str
    size_bytes: int
    line_count: int

    def __post_init__(self) -> None:
        if not self.path or not self.path.strip():
            raise ValueError("path must not be empty")
        if self.path != self.path.strip():
            raise ValueError("path must not contain surrounding whitespace")
        if self.size_bytes < 0:
            raise ValueError("size_bytes must be greater than or equal to zero")
        if self.line_count < 0:
            raise ValueError("line_count must be greater than or equal to zero")

    @property
    def is_empty(self) -> bool:
        """Return whether the source file contains no text."""

        return self.content == ""


class SourceFileAnalyzer:
    """Safely load supported source files without parsing symbols."""

    _LANGUAGE_BY_EXTENSION: ClassVar[Mapping[str, Language]] = MappingProxyType(
        {
            ".py": Language.PYTHON,
            ".ts": Language.TYPESCRIPT,
            ".tsx": Language.TYPESCRIPT,
            ".js": Language.JAVASCRIPT,
            ".jsx": Language.JAVASCRIPT,
            ".go": Language.GO,
            ".rs": Language.RUST,
            ".java": Language.JAVA,
            ".dart": Language.DART,
        }
    )

    def __init__(
        self,
        root: str | Path,
        *,
        max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES,
    ) -> None:
        if max_file_size_bytes <= 0:
            raise ValueError(
                "max_file_size_bytes must be greater than zero"
            )

        self._root = Path(root).expanduser().resolve()
        self._max_file_size_bytes = max_file_size_bytes

    @property
    def root(self) -> Path:
        """Return the configured source root."""

        return self._root

    @property
    def max_file_size_bytes(self) -> int:
        """Return the maximum accepted source-file size."""

        return self._max_file_size_bytes

    @classmethod
    def supported_extensions(cls) -> tuple[str, ...]:
        """Return supported extensions in deterministic order."""

        return tuple(sorted(cls._LANGUAGE_BY_EXTENSION))

    def analyze(self, file_path: str | Path) -> SourceFile:
        """Load one source file and return deterministic file information."""

        requested_path = Path(file_path).expanduser()
        if not requested_path.is_absolute():
            requested_path = self._root / requested_path

        resolved_path = requested_path.resolve()

        try:
            relative_path = resolved_path.relative_to(self._root)
        except ValueError as error:
            raise SourceFileOutsideRootError(
                f"source file is outside configured root: {resolved_path}"
            ) from error

        if not resolved_path.is_file():
            raise SourceFileNotFoundError(
                f"source file does not exist: {resolved_path}"
            )

        extension = resolved_path.suffix.lower()
        language = self._LANGUAGE_BY_EXTENSION.get(extension)

        if language is None:
            raise UnsupportedSourceLanguageError(
                f"unsupported source-file extension: "
                f"{extension or '<none>'}"
            )

        size_bytes = resolved_path.stat().st_size
        if size_bytes > self._max_file_size_bytes:
            raise SourceFileTooLargeError(
                "source file exceeds maximum size: "
                f"{size_bytes} > {self._max_file_size_bytes}"
            )

        raw_content = resolved_path.read_bytes()

        if b"\x00" in raw_content:
            raise BinarySourceFileError(
                f"source file contains null bytes: {relative_path.as_posix()}"
            )

        try:
            decoded_content = raw_content.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise SourceFileDecodeError(
                f"source file is not valid UTF-8: "
                f"{relative_path.as_posix()}"
            ) from error

        content = decoded_content.replace("\r\n", "\n").replace("\r", "\n")

        return SourceFile(
            path=relative_path.as_posix(),
            language=language,
            content=content,
            size_bytes=len(raw_content),
            line_count=len(content.splitlines()),
        )

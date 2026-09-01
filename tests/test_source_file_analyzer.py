# mypy: disable-error-code=misc
"""Tests for deterministic source-file analysis."""

from pathlib import Path

import pytest

from src.code_intelligence.models import Language
from src.code_intelligence.source_file_analyzer import (
    BinarySourceFileError,
    SourceFile,
    SourceFileAnalyzer,
    SourceFileDecodeError,
    SourceFileNotFoundError,
    SourceFileOutsideRootError,
    SourceFileTooLargeError,
    UnsupportedSourceLanguageError,
)


def test_analyze_python_source_file(tmp_path: Path) -> None:
    source = tmp_path / "src" / "example.py"
    source.parent.mkdir()
    raw_content = b"def run() -> int:\n    return 1\n"
    source.write_bytes(raw_content)

    result = SourceFileAnalyzer(tmp_path).analyze("src/example.py")

    assert result == SourceFile(
        path="src/example.py",
        language=Language.PYTHON,
        content="def run() -> int:\n    return 1\n",
        size_bytes=len(raw_content),
        line_count=2,
    )
    assert result.is_empty is False

def test_analyze_empty_source_file(tmp_path: Path) -> None:
    source = tmp_path / "empty.py"
    source.write_text("", encoding="utf-8")

    result = SourceFileAnalyzer(tmp_path).analyze(source)

    assert result.path == "empty.py"
    assert result.content == ""
    assert result.size_bytes == 0
    assert result.line_count == 0
    assert result.is_empty is True


@pytest.mark.parametrize(
    ("filename", "language"),
    [
        ("module.py", Language.PYTHON),
        ("module.ts", Language.TYPESCRIPT),
        ("module.tsx", Language.TYPESCRIPT),
        ("module.js", Language.JAVASCRIPT),
        ("module.jsx", Language.JAVASCRIPT),
        ("module.go", Language.GO),
        ("module.rs", Language.RUST),
        ("module.java", Language.JAVA),
        ("module.dart", Language.DART),
    ],
)
def test_detect_supported_language(
    tmp_path: Path,
    filename: str,
    language: Language,
) -> None:
    source = tmp_path / filename
    source.write_text("source\n", encoding="utf-8")

    result = SourceFileAnalyzer(tmp_path).analyze(source)

    assert result.language is language


def test_extension_detection_is_case_insensitive(
    tmp_path: Path,
) -> None:
    source = tmp_path / "MODULE.PY"
    source.write_text("value = 1\n", encoding="utf-8")

    result = SourceFileAnalyzer(tmp_path).analyze(source)

    assert result.language is Language.PYTHON


def test_utf8_bom_is_removed_from_content(tmp_path: Path) -> None:
    source = tmp_path / "bom.py"
    # Explicitly include BOM and some content
    raw_content = b"\xef\xbb\xbfvalue = 1\n"
    source.write_bytes(raw_content)

    result = SourceFileAnalyzer(tmp_path).analyze(source)

    assert result.content == "value = 1\n"
    assert result.size_bytes == len(raw_content)
    assert result.line_count == 1


def test_reject_missing_source_file(tmp_path: Path) -> None:
    analyzer = SourceFileAnalyzer(tmp_path)

    with pytest.raises(SourceFileNotFoundError):
        analyzer.analyze("missing.py")


def test_reject_directory_instead_of_file(tmp_path: Path) -> None:
    analyzer = SourceFileAnalyzer(tmp_path)

    with pytest.raises(SourceFileNotFoundError):
        analyzer.analyze(tmp_path)


def test_reject_file_outside_configured_root(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    root.mkdir()

    outside = tmp_path / "outside.py"
    outside.write_text("value = 1\n", encoding="utf-8")

    analyzer = SourceFileAnalyzer(root)

    with pytest.raises(SourceFileOutsideRootError):
        analyzer.analyze(outside)


def test_reject_unsupported_extension(tmp_path: Path) -> None:
    source = tmp_path / "notes.txt"
    source.write_text("plain text\n", encoding="utf-8")

    analyzer = SourceFileAnalyzer(tmp_path)

    with pytest.raises(UnsupportedSourceLanguageError):
        analyzer.analyze(source)


def test_reject_file_above_size_limit(tmp_path: Path) -> None:
    source = tmp_path / "large.py"
    source.write_text("12345", encoding="utf-8")

    analyzer = SourceFileAnalyzer(
        tmp_path,
        max_file_size_bytes=4,
    )

    with pytest.raises(SourceFileTooLargeError):
        analyzer.analyze(source)


def test_reject_binary_file(tmp_path: Path) -> None:
    source = tmp_path / "binary.py"
    source.write_bytes(b"value\x00data")

    analyzer = SourceFileAnalyzer(tmp_path)

    with pytest.raises(BinarySourceFileError):
        analyzer.analyze(source)


def test_reject_invalid_utf8_file(tmp_path: Path) -> None:
    source = tmp_path / "invalid.py"
    # Sequence that is invalid in UTF-8
    source.write_bytes(b"\xff\xfe\xfd")

    analyzer = SourceFileAnalyzer(tmp_path)

    with pytest.raises(SourceFileDecodeError):
        analyzer.analyze(source)


def test_supported_extensions_are_sorted() -> None:
    extensions = SourceFileAnalyzer.supported_extensions()

    assert extensions == tuple(sorted(extensions))
    assert extensions == (
        ".dart",
        ".go",
        ".java",
        ".js",
        ".jsx",
        ".py",
        ".rs",
        ".ts",
        ".tsx",
    )


def test_analyzer_exposes_configuration(tmp_path: Path) -> None:
    analyzer = SourceFileAnalyzer(
        tmp_path,
        max_file_size_bytes=512,
    )

    assert analyzer.root == tmp_path.resolve()
    assert analyzer.max_file_size_bytes == 512


@pytest.mark.parametrize("size_limit", [0, -1])
def test_reject_non_positive_size_limit(
    tmp_path: Path,
    size_limit: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="max_file_size_bytes must be greater than zero",
    ):
        SourceFileAnalyzer(
            tmp_path,
            max_file_size_bytes=size_limit,
        )


@pytest.mark.parametrize(
    ("path", "size_bytes", "line_count", "message"),
    [
        ("", 0, 0, "path must not be empty"),
        (
            " example.py",
            0,
            0,
            "path must not contain surrounding whitespace",
        ),
        (
            "example.py",
            0,
            -1,
            "line_count must be greater than or equal to zero",
        ),
        (
            "example.py",
            -1,
            0,
            "size_bytes must be greater than or equal to zero",
        ),
    ],
)
def test_source_file_rejects_invalid_state(
    path: str,
    size_bytes: int,
    line_count: int,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        SourceFile(
            path=path,
            language=Language.PYTHON,
            content="",
            size_bytes=size_bytes,
            line_count=line_count,
        )

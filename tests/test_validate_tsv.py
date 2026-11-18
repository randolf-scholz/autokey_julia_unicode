"""Check the TSV contract, error recovery, and command-line diagnostics."""

from pathlib import Path

import pytest
from src.validate_tsv import (
    ROOT,
    SCHEMA_PATH,
    TSVSchema,
    ValidationStats,
    main,
    validate_tsv,
)

ICONS_FILENAME = "icons-julia.tsv"
LATEX_SCHEMA = ROOT / "data/schemas/latex.toml"
HEADER = "code_points\tchars\ttab_completions\tunicode_name\n"
ROW = "U+0041\tA\t\\A\tLATIN CAPITAL LETTER A\n"


@pytest.fixture
def unicode_tsv(tmp_path: Path) -> Path:
    path = tmp_path / "unicode.tsv"
    path.write_text(
        "unicode_name\tcode_points\tchars\n"
        "LATIN CAPITAL LETTER A\tU+0041\tA\n"
        "\tU+000A\t\n"
        "GRINNING FACE\tU+1F600\t😀\n"
    )
    return path


# Each case exercises a distinct serialization or field constraint.
@pytest.mark.parametrize(
    "row",
    [
        ROW,
        "",
        "\n",
        ROW.rstrip("\n"),
        ROW.replace("\n", "\r\n"),
        "U+0041\t\t\\A\tLATIN CAPITAL LETTER A\n",
        "U+0009\t\t\t\n",
        "U+000D, U+000A\t\t\t\n",
        'U+0022\t"\t\\quote\tQUOTATION MARK\n',
        "U+005C, U+006E\t\\n\t\t\n",
        "U+000B\t\v\t\t\n",
        "U+0000\t\0\t\t\n",
        "U+0020\t \t\tSPACE\n",
        "U+0041, U+0041\tAA\t\\AA\t\n",
        "U+0301\t́\t\\acute\tCOMBINING ACUTE ACCENT\n",
        "U+0065, U+0301\té\t\\eacute\tCustom sequence name\n",
        "U+0041\tA\t\tLATIN CAPITAL LETTER A\n",
        "U+0041\tA\t\\A, \\a\tLATIN CAPITAL LETTER A\n",
        "U+0041\tA\t\\,\tLATIN CAPITAL LETTER A\n",
        "U+FF3C\t＼\t\\fw\\\tFULLWIDTH REVERSE SOLIDUS\n",
    ],
)
def test_valid_icon_records(tmp_path: Path, row: str) -> None:
    path = tmp_path / ICONS_FILENAME
    contents = (HEADER + row).encode()
    path.write_bytes(contents)
    assert list(validate_tsv(path)) == []
    assert path.read_bytes() == contents


@pytest.mark.parametrize(
    "contents, error",
    [
        ("", "missing header"),
        ("code_points\tchars\n", "missing required columns"),
        (HEADER.rstrip("\n") + "\tchars\n", "duplicate header"),
        (HEADER + "U+0041\tA\t\\A\n", "expected 4 fields"),
        (HEADER + ROW.rstrip("\n") + "\textra\n", "expected 4 fields"),
        (HEADER + "\tA\t\\A\t\n", "code_points: must not be empty"),
        (HEADER + "U+0041, \tA\t\t\n", "empty list item"),
        (HEADER + "U+0041,U+0041\tAA\t\t\n", "invalid item pattern"),
        (HEADER + "U+41\tA\t\t\n", "invalid item pattern"),
        (HEADER + "U+03b1\tα\t\t\n", "invalid item pattern"),
        (HEADER + "U+D800\t\t\t\n", "invalid Unicode scalar value"),
        (HEADER + "U+110000\t\t\t\n", "invalid Unicode scalar value"),
        (HEADER + ROW.replace("\\A", "A"), "tab_completions: invalid item pattern"),
        (HEADER + ROW.replace("\\A", "\\A "), "tab_completions: invalid item pattern"),
        (HEADER + ROW.replace("\\A", "\\α"), "tab_completions: invalid item pattern"),
        (HEADER + ROW.replace("\\A", "\\A, \\A"), "duplicate list item"),
        (HEADER + 'U+0009\t"\t"\t\t\n', "expected 4 fields"),
        (HEADER + 'U+0022\t""\t\t\n', "chars: does not match code_points"),
    ],
)
def test_invalid_icon_records_report_file(
    tmp_path: Path, contents: str, error: str
) -> None:
    path = tmp_path / ICONS_FILENAME
    path.write_text(contents)
    errors = list(validate_tsv(path))
    assert errors
    assert error in "\n".join(map(str, errors))
    assert all(str(path) in str(item) for item in errors)


@pytest.mark.parametrize(
    "points, chars",
    [
        ("U+0041", "N"),
        ("U+0301", "\u00a0́\u00a0"),
        ("U+0065, U+0301", "é"),
        ("U+0041, U+000A", "A"),
        ("U+1F600, U+FE0F", "😀"),
        ("U+1F600", "😀️"),
        ("U+1F600, U+FE0F", "😀︎"),
    ],
)
def test_exact_replacement_identity_is_checked_without_name_checks(
    tmp_path: Path, points: str, chars: str
) -> None:
    path = tmp_path / ICONS_FILENAME
    path.write_text(HEADER + f"{points}\t{chars}\t\t\n")
    assert "chars: does not match code_points" in "\n".join(
        map(str, validate_tsv(path))
    )


@pytest.mark.parametrize("point", [0xFE00, 0xFE0F, 0xE0100, 0xE01EF])
def test_variation_selectors_are_preserved_and_use_base_name(
    tmp_path: Path, unicode_tsv: Path, point: int
) -> None:
    path = tmp_path / ICONS_FILENAME
    path.write_text(
        HEADER + f"U+1F600, U+{point:04X}\t😀{chr(point)}\t\tGrinning Face\n"
    )
    assert list(validate_tsv(path, check_icons=True, unicode_tsv=unicode_tsv)) == []
    path.write_text(path.read_text().replace("Grinning Face", "Wrong name"))
    assert "unicode_name: expected" in "\n".join(
        map(str, validate_tsv(path, check_icons=True, unicode_tsv=unicode_tsv))
    )


@pytest.mark.parametrize(
    "row, valid",
    [
        (ROW.replace("LATIN CAPITAL LETTER A", "Latin Capital Letter A"), True),
        (ROW.replace("LATIN CAPITAL LETTER A", ""), False),
        (ROW.replace("LATIN CAPITAL LETTER A", "LATIN CAPITAL LETTER A "), False),
        ("U+E001\t\t\tCustom name\n", True),
        ("U+0065, U+0301\té\t\tCustom sequence name\n", True),
        ("U+000A\t\t\tLINE FEED (LF)\n", False),
    ],
)
def test_unicode_name_contract(
    tmp_path: Path, unicode_tsv: Path, row: str, valid: bool
) -> None:
    path = tmp_path / ICONS_FILENAME
    path.write_text(HEADER + row)
    errors = list(validate_tsv(path, check_icons=True, unicode_tsv=unicode_tsv))
    assert bool(errors) is not valid


def test_headers_use_names_and_allow_extra_metadata(tmp_path: Path) -> None:
    path = tmp_path / ICONS_FILENAME
    path.write_text(
        "notes\tunicode_name\ttab_completions\tchars\tcode_points\n"
        "extra\tLATIN CAPITAL LETTER A\t\\A\tA\tU+0041\n"
    )
    assert list(validate_tsv(path)) == []


def test_latex_schema_validates_optional_chars_and_mode(tmp_path: Path) -> None:
    path = tmp_path / "latex.tsv"
    path.write_text("code_points\tmode\tlatex_code\nU+03B1\tmath\t\\alpha\n")
    assert list(validate_tsv(path, schema_path=LATEX_SCHEMA)) == []
    path.write_text(
        "code_points\tchars\tmode\tlatex_code\nU+03B1\t\tinvalid\t\\alpha\n"
    )
    errors = "\n".join(map(str, validate_tsv(path, schema_path=LATEX_SCHEMA)))
    assert "chars: must not be empty" in errors
    assert "mode: invalid item pattern" in errors


@pytest.mark.parametrize(
    "before, after, row, error",
    [
        ("min_items = 1", "min_items = 2", ROW, "too few list items"),
        (
            "item_pattern = '[^\\t\\r\\n]*'",
            "item_pattern = 'NEVER'",
            ROW,
            "invalid item pattern",
        ),
        (
            "allow_unknown_columns = true",
            "allow_unknown_columns = false",
            "",
            "unknown columns",
        ),
    ],
)
def test_constraints_come_from_schema(
    tmp_path: Path, before: str, after: str, row: str, error: str
) -> None:
    schema = tmp_path / "schema.toml"
    source = SCHEMA_PATH.read_text()
    assert before in source
    schema.write_text(source.replace(before, after))
    path = tmp_path / ICONS_FILENAME
    path.write_text(HEADER + row if row else HEADER.rstrip("\n") + "\textra\n")
    assert error in "\n".join(map(str, validate_tsv(path, schema_path=schema)))


@pytest.mark.parametrize("replacement", ['"chars"', '"unknown"'])
def test_schema_rejects_duplicate_or_undefined_required_columns(
    tmp_path: Path, replacement: str
) -> None:
    schema = tmp_path / "schema.toml"
    schema.write_text(SCHEMA_PATH.read_text().replace('"unicode_name"', replacement, 1))
    with pytest.raises(ValueError, match="required_columns"):
        TSVSchema.from_spec(schema)


def test_reader_uses_schema_encoding_delimiter_and_quoting(tmp_path: Path) -> None:
    schema = tmp_path / "schema.toml"
    schema.write_text(
        SCHEMA_PATH.read_text()
        .replace('encoding = "utf-8"', 'encoding = "utf-16"')
        .replace('delimiter = "\\t"', 'delimiter = ";"')
        .replace('quoting = "none"', 'quoting = "minimal"')
    )
    path = tmp_path / ICONS_FILENAME
    path.write_bytes(
        (
            "code_points;chars;tab_completions;unicode_name\n"
            'U+0041;"A";\\A;LATIN CAPITAL LETTER A\n'
        ).encode("utf-16")
    )
    assert list(validate_tsv(path, schema_path=schema)) == []


def test_validation_recovers_from_row_errors_and_counts_valid_rows(
    tmp_path: Path,
) -> None:
    path = tmp_path / ICONS_FILENAME
    path.write_text(HEADER + "bad\tA\talias\t\n" + "U+0041\tN\t\\A\t\n" + ROW)
    stats = ValidationStats()
    errors = list(validate_tsv(path, stats=stats))
    assert stats == ValidationStats(rows_validated=1, rows_total=3)
    assert len(errors) == 3
    assert ":2: code_points:" in str(errors[0])
    assert ":2: tab_completions:" in str(errors[1])
    assert ":3: chars:" in str(errors[2])


def test_validation_recovers_from_csv_parse_error(tmp_path: Path) -> None:
    schema = tmp_path / "schema.toml"
    schema.write_text(
        SCHEMA_PATH.read_text().replace('quoting = "none"', 'quoting = "minimal"')
    )
    path = tmp_path / ICONS_FILENAME
    path.write_text(HEADER + '"U+0041"x\tA\t\\A\t\n' + ROW)
    stats = ValidationStats()
    errors = list(validate_tsv(path, schema_path=schema, stats=stats))
    assert len(errors) == 1
    assert ":2: invalid TSV:" in str(errors[0])
    assert stats == ValidationStats(rows_validated=1, rows_total=2)


def test_command_line_icon_checks_are_opt_in(
    tmp_path: Path, unicode_tsv: Path, capsys
) -> None:
    path = tmp_path / ICONS_FILENAME
    path.write_text(HEADER + ROW.replace("LATIN CAPITAL LETTER A", "Incorrect name"))
    args = ["--unicode-tsv", str(unicode_tsv), str(path)]
    assert main(args) == 0
    assert capsys.readouterr() == ("", "")
    assert main([*args, "--check-icons"]) == 1
    assert "unicode_name: expected" in capsys.readouterr().err


def test_cli_continues_after_missing_files_bad_headers_and_encoding(
    tmp_path: Path, capsys
) -> None:
    (tmp_path / "bad-header.tsv").write_text("code_points\tchars\n")
    (tmp_path / "bad-encoding.tsv").write_bytes(b"\xff")
    (tmp_path / "valid.tsv").write_text(HEADER + ROW)
    assert (
        main(["--verbose", str(tmp_path / "missing*.tsv"), str(tmp_path / "*.tsv")])
        == 1
    )
    output = capsys.readouterr()
    assert "No files match" in output.err
    assert "invalid UTF-8" in output.err
    assert "missing required columns" in output.err
    assert "3 errors found" in output.err
    assert "valid.tsv: 1/1 rows validated" in output.out
    assert "1/3 files validated" in output.out


def test_cli_counts_valid_rows_on_failure(tmp_path: Path, capsys) -> None:
    path = tmp_path / ICONS_FILENAME
    path.write_text(HEADER + "bad\n" + ROW)
    assert main(["--verbose", str(path)]) == 1
    output = capsys.readouterr()
    assert "1/2 rows validated" in output.out
    assert "0/1 files validated" in output.out
    assert ":2: expected 4 fields" in output.err


@pytest.mark.parametrize(
    "pattern, count", [(".", 2), ("*.tsv", 2), ("**/*.tsv", 3), ("literal[1].tsv", 1)]
)
def test_cli_directories_globs_and_literal_paths(
    tmp_path: Path, capsys, pattern: str, count: int
) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    for path in (
        tmp_path / "first file.tsv",
        tmp_path / "literal[1].tsv",
        nested / "second.tsv",
    ):
        path.write_text(HEADER)
    (tmp_path / "not-a-file.tsv").mkdir()
    assert main(["--verbose", str(tmp_path / pattern)]) == 0
    assert f"{count}/{count} files validated" in capsys.readouterr().out


def test_missing_schema_is_a_diagnostic(tmp_path: Path, capsys) -> None:
    path = tmp_path / ICONS_FILENAME
    path.write_text(HEADER)
    missing = tmp_path / "missing.toml"
    assert main(["--schema", str(missing), str(path)]) == 1
    assert str(missing) in capsys.readouterr().err

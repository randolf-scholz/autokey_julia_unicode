"""Check UCD filtering, serialization, and preservation of existing exports."""

import csv
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from src import import_ucd as ucd
from src.validate_tsv import validate_tsv

HEADER = ["code_points", "chars", "tab_completions", "unicode_name"]


def write_input(source: Path, blocks: str, records: list[tuple[int, str]]) -> None:
    source.mkdir(parents=True, exist_ok=True)
    (source / "Blocks.txt").write_text(blocks)
    (source / "NameAliases.txt").write_text("# Synthetic aliases\n")
    with (source / "UnicodeData.txt").open("w", encoding="utf8", newline="") as target:
        writer = csv.writer(target, delimiter=";", lineterminator="\n")
        for point, name in records:
            writer.writerow([f"{point:04X}", name, "Lo", "0", "L", *([""] * 10)])


def read_output(path: Path) -> list[list[str]]:
    with path.open(encoding="utf8", newline="") as source:
        return list(csv.reader(source, delimiter="\t", quoting=csv.QUOTE_NONE))


def snapshot(path: Path) -> dict[Path, bytes]:
    return {file.relative_to(path): file.read_bytes() for file in path.rglob("*.tsv")}


def test_import_sorts_records_and_writes_block_and_character_indexes() -> None:
    with TemporaryDirectory() as tmpdir:
        directory = Path(tmpdir)
        source = directory / "source"

        # Supply unsorted records, block comments, and a block without characters.
        write_input(
            source,
            "# Comment\n0000..007F; Basic Latin # comment\n"
            "1F600..1F64F; Emoticons\n1FA00..1FA6F; Empty Block\n",
            [
                (0x1F600, "GRINNING FACE"),
                (0x61, "LATIN SMALL LETTER A"),
                (0x41, "LATIN CAPITAL LETTER A"),
            ],
        )

        output = directory / "output"
        assert ucd.main(["--source-dir", str(source), "--output-dir", str(output)]) == 0

        # Each block export contains its characters in code point order.
        expected = [
            HEADER,
            ["U+0041", "A", "", "LATIN CAPITAL LETTER A"],
            ["U+0061", "a", "", "LATIN SMALL LETTER A"],
        ]
        assert read_output(output / "[000000-00007F]-basic_latin.tsv") == expected

        expected = [HEADER, ["U+1F600", "😀", "", "GRINNING FACE"]]
        assert read_output(output / "[01F600-01F64F]-emoticons.tsv") == expected

        # Empty blocks still receive a header-only export and an index entry.
        assert read_output(output / "[01FA00-01FA6F]-empty_block.tsv") == [HEADER]

        expected_blocks = [
            ["block_start", "block_end", "block_name"],
            ["0000", "007F", "Basic Latin"],
            ["1F600", "1F64F", "Emoticons"],
            ["1FA00", "1FA6F", "Empty Block"],
        ]
        assert read_output(directory / "blocks.tsv") == expected_blocks

        # The character index combines all block exports under a single header.
        expected_characters = [HEADER]
        for path in sorted(output.glob("*.tsv")):
            expected_characters.extend(read_output(path)[1:])
            assert list(validate_tsv(path)) == []

        assert read_output(directory / "unicode.tsv") == expected_characters


def test_control_cells_are_omitted_and_quotes_remain_literal() -> None:
    with TemporaryDirectory() as tmpdir:
        directory = Path(tmpdir)
        source = directory / "source"
        points = [(p, "<control>") for p in [0x00, 0x09, 0x0A, 0x0B, 0x0C, 0x0D]]
        points.extend([(0x22, "QUOTATION MARK"), (0x5C, "REVERSE SOLIDUS")])
        write_input(source, "0000..007F; Basic Latin\n", points)
        (source / "NameAliases.txt").write_text(
            "0000;NULL;control\n0009;CHARACTER TABULATION;control\n"
            "000A;LINE FEED;control\n000B;LINE TABULATION;control\n"
            "000C;FORM FEED;control\n000D;CARRIAGE RETURN;control\n"
        )
        output = directory / "output"
        ucd.import_ucd(source, output)
        path = output / "[000000-00007F]-basic_latin.tsv"
        actual = [row[1] for row in read_output(path)[1:]]
        expected = ["\0", "", "", "\v", "\f", "", '"', "\\"]
        assert actual == expected
        assert path.read_bytes().count(b"\n") == len(points) + 1
        assert b'U+0022\t"\t\tQUOTATION MARK\n' in path.read_bytes()
        assert list(validate_tsv(path)) == []


def test_first_alias_fills_empty_names_without_replacing_formal_names(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    write_input(
        source,
        "0000..007F; Basic Latin\n",
        [(0, ""), (0x41, "LATIN CAPITAL LETTER A"), (0x7F, "<control>")],
    )
    (source / "NameAliases.txt").write_text(
        "# File order, not alias type, determines the fallback.\n"
        "0000;NULL;control\n0000;NUL;abbreviation\n"
        "0041;ALTERNATE LETTER A;correction\n"
        "007F;DEL;abbreviation\n007F;DELETE;control\n"
    )
    output = tmp_path / "blocks"
    ucd.import_ucd(source, output)
    rows = read_output(tmp_path / "unicode.tsv")[1:]
    assert [row[3] for row in rows] == ["NULL", "LATIN CAPITAL LETTER A", "DEL"]
    assert list(validate_tsv(tmp_path / "unicode.tsv")) == []


def test_missing_name_and_alias_preserves_existing_exports(tmp_path: Path) -> None:
    source = tmp_path / "source"
    write_input(source, "0000..007F; Basic Latin\n", [(0x41, "LATIN CAPITAL LETTER A")])
    output = tmp_path / "blocks"
    ucd.import_ucd(source, output)
    before = snapshot(tmp_path)
    write_input(source, "0000..007F; Basic Latin\n", [(0x7F, "<control>")])
    with pytest.raises(ValueError, match="no name or alias for U\\+007F"):
        ucd.import_ucd(source, output)
    assert snapshot(tmp_path) == before


def test_ranges_endpoints_and_surrogates_are_skipped() -> None:
    with TemporaryDirectory() as tmpdir:
        directory = Path(tmpdir)
        source = directory / "source"
        write_input(
            source,
            "2200..22FF; Mathematical Operators\n3400..4DBF; CJK\n"
            "D800..DB7F; High Surrogates\n",
            [
                (0x2200, "FOR ALL"),
                (0x3400, "<CJK, First>"),
                (0x4DBF, "<CJK, Last>"),
                (0xD800, "<surrogate>"),
            ],
        )
        output = directory / "output"
        ucd.import_ucd(source, output)
        assert read_output(output / "[003400-004DBF]-cjk.tsv") == [HEADER]
        assert read_output(output / "[00D800-00DB7F]-high_surrogates.tsv") == [HEADER]
        expected = [HEADER, ["U+2200", "∀", "", "FOR ALL"]]
        assert read_output(directory / "unicode.tsv") == expected


def test_regeneration_removes_obsolete_exports_and_is_deterministic() -> None:
    with TemporaryDirectory() as tmpdir:
        directory = Path(tmpdir)
        source = directory / "source"
        write_input(
            source,
            "0000..007F; Basic Latin\n",
            [(0x41, "LATIN CAPITAL LETTER A")],
        )
        output = directory / "output"
        output.mkdir()
        obsolete = output / "[000080-0000FF]-old_block.tsv"
        obsolete.write_text("old export")
        notes = output / "notes.tsv"
        notes.write_text("keep")
        ucd.import_ucd(source, output)
        first = snapshot(directory)
        ucd.import_ucd(source, output)
        assert snapshot(directory) == first
        assert not obsolete.exists()
        assert notes.read_text() == "keep"


@pytest.mark.parametrize(
    ("filename", "invalid"),
    [
        ("UnicodeData.txt", "bad;record\n"),
        ("UnicodeData.txt", ""),
        ("NameAliases.txt", "bad;record\n"),
        ("Blocks.txt", "007F..0000; Reversed\n"),
        ("Blocks.txt", "0000..007F; First\n0070..00FF; Overlap\n"),
    ],
)
def test_bad_input_preserves_existing_exports(filename: str, invalid: str) -> None:
    with (
        TemporaryDirectory() as tmpdir,
        redirect_stderr(StringIO()) as stderr,
    ):
        directory = Path(tmpdir)
        source = directory / "source"
        write_input(
            source,
            "0000..007F; Basic Latin\n",
            [(0x41, "LATIN CAPITAL LETTER A")],
        )
        output = directory / "output"
        ucd.import_ucd(source, output)
        before = snapshot(directory)
        (source / filename).write_text(invalid)
        assert ucd.main(["--source-dir", str(source), "--output-dir", str(output)]) == 1
        assert "error:" in stderr.getvalue()
        assert snapshot(directory) == before

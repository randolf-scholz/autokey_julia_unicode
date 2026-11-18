"""Check UCD filtering, serialization, and preservation of existing exports."""

import csv
from pathlib import Path

import pytest
from src import import_ucd as ucd
from src.validate_tsv import validate_tsv

HEADER = ["code_points", "chars", "tab_completions", "unicode_name"]


@pytest.fixture
def source(tmp_path: Path) -> Path:
    path = tmp_path / "source"
    path.mkdir()
    return path


def write_input(source: Path, blocks: str, records: list[tuple[int, str]]):
    (source / "Blocks.txt").write_text(blocks)
    with (source / "UnicodeData.txt").open("w", encoding="utf8", newline="") as target:
        writer = csv.writer(target, delimiter=";", lineterminator="\n")
        for point, name in records:
            writer.writerow([f"{point:04X}", name, "Lo", "0", "L", *([""] * 10)])


def read_output(path: Path) -> list[list[str]]:
    with path.open(encoding="utf8", newline="") as source:
        return list(csv.reader(source, delimiter="\t", quoting=csv.QUOTE_NONE))


def snapshot(path: Path) -> dict[Path, bytes]:
    return {file.relative_to(path): file.read_bytes() for file in path.rglob("*.tsv")}


def test_import_sorts_records_and_writes_block_and_character_indexes(
    source: Path, tmp_path: Path
):
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
    output = tmp_path / "output"
    assert ucd.main(["--source-dir", str(source), "--output-dir", str(output)]) == 0
    assert read_output(output / "[000000-00007F]-basic_latin.tsv") == [
        HEADER,
        ["U+0041", "A", "", "LATIN CAPITAL LETTER A"],
        ["U+0061", "a", "", "LATIN SMALL LETTER A"],
    ]
    assert read_output(output / "[01F600-01F64F]-emoticons.tsv") == [
        HEADER,
        ["U+1F600", "😀", "", "GRINNING FACE"],
    ]
    assert read_output(output / "[01FA00-01FA6F]-empty_block.tsv") == [HEADER]
    assert read_output(tmp_path / "blocks.tsv") == [
        ["block_start", "block_end", "block_name"],
        ["0000", "007F", "Basic Latin"],
        ["1F600", "1F64F", "Emoticons"],
        ["1FA00", "1FA6F", "Empty Block"],
    ]
    rows = [HEADER]
    for path in sorted(output.glob("*.tsv")):
        rows.extend(read_output(path)[1:])
        assert list(validate_tsv(path)) == []
    assert read_output(tmp_path / "unicode.tsv") == rows


def test_control_cells_are_omitted_and_quotes_remain_literal(
    source: Path, tmp_path: Path
):
    points = [0x00, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x22, 0x5C]
    write_input(
        source, "0000..007F; Basic Latin\n", [(point, "<control>") for point in points]
    )
    output = tmp_path / "output"
    ucd.import_ucd(source, output)
    path = output / "[000000-00007F]-basic_latin.tsv"
    assert [row[1] for row in read_output(path)[1:]] == [
        "\0",
        "",
        "",
        "\v",
        "\f",
        "",
        '"',
        "\\",
    ]
    assert path.read_bytes().count(b"\n") == len(points) + 1
    assert b'U+0022\t"\t\t\n' in path.read_bytes()
    assert list(validate_tsv(path)) == []


def test_ranges_endpoints_and_surrogates_are_skipped(source: Path, tmp_path: Path):
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
    output = tmp_path / "output"
    ucd.import_ucd(source, output)
    assert read_output(output / "[003400-004DBF]-cjk.tsv") == [HEADER]
    assert read_output(output / "[00D800-00DB7F]-high_surrogates.tsv") == [HEADER]
    assert read_output(tmp_path / "unicode.tsv") == [
        HEADER,
        ["U+2200", "∀", "", "FOR ALL"],
    ]


def test_regeneration_removes_obsolete_exports_and_is_deterministic(
    source: Path, tmp_path: Path
):
    write_input(source, "0000..007F; Basic Latin\n", [(0x41, "LATIN CAPITAL LETTER A")])
    output = tmp_path / "output"
    output.mkdir()
    obsolete = output / "[000080-0000FF]-old_block.tsv"
    obsolete.write_text("old export")
    notes = output / "notes.tsv"
    notes.write_text("keep")
    ucd.import_ucd(source, output)
    first = snapshot(tmp_path)
    ucd.import_ucd(source, output)
    assert snapshot(tmp_path) == first
    assert not obsolete.exists()
    assert notes.read_text() == "keep"


@pytest.mark.parametrize(
    "filename, invalid",
    [
        ("UnicodeData.txt", "bad;record\n"),
        ("UnicodeData.txt", ""),
        ("Blocks.txt", "007F..0000; Reversed\n"),
        ("Blocks.txt", "0000..007F; First\n0070..00FF; Overlap\n"),
    ],
)
def test_bad_input_preserves_existing_exports(
    source: Path, tmp_path: Path, capsys, filename: str, invalid: str
):
    write_input(source, "0000..007F; Basic Latin\n", [(0x41, "LATIN CAPITAL LETTER A")])
    output = tmp_path / "output"
    ucd.import_ucd(source, output)
    before = snapshot(tmp_path)
    (source / filename).write_text(invalid)
    assert ucd.main(["--source-dir", str(source), "--output-dir", str(output)]) == 1
    assert "error:" in capsys.readouterr().err
    assert snapshot(tmp_path) == before

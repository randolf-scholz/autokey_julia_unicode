#!/usr/bin/env python3
"""Import Unicode data into TSV files with ``python src/import_ucd.py``.

Read Blocks.txt and UnicodeData.txt from third_party/ucd. Write schema-compliant
tables to data/ucd/blocks, their concatenation to data/ucd/unicode.tsv, and
the block index to data/ucd/blocks.tsv. Skip UnicodeData's First/Last ranges,
including their endpoint records, to keep the symbol tables compact.
Omit surrogates because they cannot be encoded as standalone UTF-8 symbols.
"""

import argparse
import csv
import re
import sys
import tomllib
from bisect import bisect_left, bisect_right
from collections.abc import Iterable, Sequence
from enum import StrEnum
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import NamedTuple

PROJECT_DIR = Path(__file__).resolve().parents[1]
UCD_DIR = PROJECT_DIR / "third_party" / "ucd"
ICON_DIR = PROJECT_DIR / "data" / "ucd" / "blocks"
SCHEMA_PATH = PROJECT_DIR / "data" / "schemas" / "icons.toml"
EXCLUDED_CHARS = frozenset("\t\r\n")
UNICODE_DATA_FIELD_COUNT = 15
MAX_CODE_POINT = 0x10FFFF
SURROGATE_START = 0xD800
SURROGATE_END = 0xDFFF
BLOCK_FILENAME = re.compile(r"\[[0-9A-F]{6}-[0-9A-F]{6}\]-.+\.tsv")


class Header(StrEnum):
    """Icon TSV columns in the schema's canonical export order."""

    CODE_POINTS = "code_points"
    CHARS = "chars"
    TAB_COMPLETIONS = "tab_completions"
    UNICODE_NAME = "unicode_name"


def validate_header(path: Path = SCHEMA_PATH) -> None:
    """Reject schema changes that would make the exported columns inconsistent."""
    with path.open("rb") as source:
        schema = tomllib.load(source)
    if list(Header) != schema["format"]["required_columns"]:
        raise ValueError(f"{path}: Header must match format.required_columns exactly")
    if not set(Header) <= schema["columns"].keys():
        raise ValueError(f"{path}: Header must match the defined columns")


class UnicodeEntry(NamedTuple):
    """The four schema columns of each character row."""

    code_points: str
    chars: str
    tab_completions: str = ""
    unicode_name: str = ""


class UnicodeBlock(NamedTuple):
    """A named, inclusive range from Blocks.txt."""

    name: str
    start: int
    end: int

    @property
    def filename(self) -> str:
        slug = self.name.lower().replace(" ", "_")
        return f"[{self.start:06X}-{self.end:06X}]-{slug}.tsv"


def read_blocks(path: Path) -> list[UnicodeBlock]:
    """Read block ranges, ignoring blank lines and Unicode's comments."""
    blocks = []
    with path.open(encoding="utf-8", newline="") as source:
        for line_number, line in enumerate(source, start=1):
            line = line.partition("#")[0].strip()
            if not line:
                continue
            code_range, name = (field.strip() for field in line.split(";"))

            # Bounds are inclusive hexadecimal code points.
            start, end = (int(bound, 16) for bound in code_range.split(".."))
            if not name or not 0 <= start <= end <= MAX_CODE_POINT:
                raise ValueError(f"{path}:{line_number}: invalid block")

            if blocks and start <= blocks[-1].end:
                raise ValueError(
                    f"{path}:{line_number}: overlapping or unsorted blocks"
                )
            blocks.append(UnicodeBlock(name, start, end))

    if not blocks:
        raise ValueError(f"{path}: no blocks found")
    return blocks


def read_unicode_names(path: Path) -> dict[int, str]:
    """Read explicit scalar records, omitting First/Last ranges and surrogates."""
    names = {}
    has_records = False
    with path.open(encoding="utf-8", newline="") as source:
        # UnicodeData has 15 unquoted fields; the first two are code point and name.
        for line_number, line in enumerate(source, start=1):
            line = line.rstrip("\r\n")
            if not line:
                continue
            row = line.split(";")
            if len(row) != UNICODE_DATA_FIELD_COUNT:
                raise ValueError(
                    f"{path}:{line_number}: "
                    f"expected {UNICODE_DATA_FIELD_COUNT} UnicodeData fields"
                )
            point = int(row[0], 16)
            if not 0 <= point <= MAX_CODE_POINT:
                raise ValueError(f"{path}:{line_number}: invalid code point")
            has_records = True

            name = row[1]
            if name.endswith((", First>", ", Last>")):
                continue
            # Surrogate and range-only block files receive just the header.
            if SURROGATE_START <= point <= SURROGATE_END:
                continue
            if point in names:
                raise ValueError(f"{path}:{line_number}: duplicate code point")
            names[point] = "" if name.startswith("<") else name

    if not has_records:
        raise ValueError(f"{path}: no Unicode records found")
    return names


def write_tsv(
    path: Path, entries: Iterable[Iterable[str]], *, header: Iterable[str]
) -> None:
    """Write unquoted UTF-8 TSV, rejecting delimiters inside fields."""
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.writer(
            target,
            delimiter="\t",
            lineterminator="\n",
            quoting=csv.QUOTE_NONE,
            quotechar=None,
            escapechar=None,
        )
        writer.writerow(header)
        writer.writerows(entries)


def import_ucd(source_dir: Path = UCD_DIR, output_dir: Path = ICON_DIR) -> int:
    """Generate block TSVs and sibling blocks.tsv and unicode.tsv summary files.

    output_dir is the block directory; its parent receives the two summary files.
    Remove obsolete block files with generated names after a successful export.
    """
    validate_header()
    blocks = read_blocks(source_dir / "Blocks.txt")
    names = read_unicode_names(source_dir / "UnicodeData.txt")
    points = sorted(names)
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    with TemporaryDirectory(prefix=".ucd-export-", dir=output_dir.parent) as temporary:
        staging = Path(temporary)
        write_tsv(
            staging / "blocks.tsv",
            (
                (f"{block.start:04X}", f"{block.end:04X}", block.name)
                for block in blocks
            ),
            header=("block_start", "block_end", "block_name"),
        )

        all_entries = []
        for block in blocks:
            first = bisect_left(points, block.start)
            stop = bisect_right(points, block.end)
            entries = [
                UnicodeEntry(
                    code_points=f"U+{point:04X}",
                    chars="" if chr(point) in EXCLUDED_CHARS else chr(point),
                    unicode_name=names[point],
                )
                for point in points[first:stop]
            ]
            write_tsv(staging / block.filename, entries, header=Header)
            all_entries.extend(entries)
        write_tsv(staging / "unicode.tsv", all_entries, header=Header)

        # Finish generating every file before replacing existing exports.
        for block in blocks:
            (staging / block.filename).replace(output_dir / block.filename)
        for filename in ("blocks.tsv", "unicode.tsv"):
            (staging / filename).replace(output_dir.parent / filename)

    # Remove obsolete block exports, preserving files with unrelated names.
    generated = {block.filename for block in blocks}
    for path in output_dir.glob("*.tsv"):
        if BLOCK_FILENAME.fullmatch(path.name) and path.name not in generated:
            path.unlink()

    return len(blocks)


def main(argv: Sequence[str] | None = None) -> int:
    """Import the locally fetched UCD using paths independent of the cwd."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=UCD_DIR,
        help="UCD directory (default: %(default)s)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ICON_DIR,
        help="block directory; summary TSVs go in its parent (default: %(default)s)",
    )
    args = parser.parse_args(argv)
    try:
        count = import_ucd(args.source_dir, args.output_dir)
    except (OSError, ValueError, csv.Error) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"Generated {count} Unicode blocks to {args.output_dir.resolve()}")
    print(f"Generated blocks.tsv and unicode.tsv to {args.output_dir.resolve().parent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

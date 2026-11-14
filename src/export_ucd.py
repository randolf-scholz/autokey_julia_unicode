#!/usr/bin/env python3
"""Export per-block Unicode TSV files with ``python src/export_ucd.py``.

Read Blocks.txt and UnicodeData.txt from third_party/ucd and write icons/ucd.
As in extract_blocks.ipynb, only explicit UnicodeData records are exported;
First/Last range markers are not expanded. Surrogate records are omitted because
their code points cannot be encoded as standalone UTF-8 symbols.
"""

import argparse
import csv
import re
import sys
from bisect import bisect_left, bisect_right
from collections.abc import Iterable
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import NamedTuple

if sys.version_info < (3, 12, 3):
    raise SystemExit(
        "export_ucd.py requires Python 3.12.3 or newer for correct CSV quoting."
    )

PROJECT_DIR = Path(__file__).resolve().parents[1]
UCD_DIR = PROJECT_DIR / "third_party" / "ucd"
ICON_DIR = PROJECT_DIR / "icons" / "ucd"
BLOCKS_FILENAME = "Blocks.txt"
UNICODE_DATA_FILENAME = "UnicodeData.txt"
UNICODE_DATA_FIELD_COUNT = 15
MAX_CODE_POINT = 0x10FFFF
SURROGATE_START = 0xD800
SURROGATE_END = 0xDFFF
BLOCK_FILENAME = re.compile(r"\[[0-9A-F]{6}-[0-9A-F]{6}\]-.+\.tsv")


class UnicodeEntry(NamedTuple):
    """The seven columns used by the notebook's TSV exports."""

    code_point: str
    symbol: str
    block: str
    block_name: str
    name: str
    tab_completion: str | None = None
    latex_code: str | None = None


class UnicodeBlock(NamedTuple):
    """A named, inclusive range from Blocks.txt."""

    code_range: str
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
        # Strip both full-line and trailing comments before parsing the fields.
        lines = (line.partition("#")[0] for line in source)
        reader = csv.reader(lines, delimiter=";", quoting=csv.QUOTE_NONE)

        for row in reader:
            if not row or not any(field.strip() for field in row):
                continue
            if len(row) != 2:
                raise ValueError(f"{path}:{reader.line_num}: expected two block fields")
            code_range, name = (field.strip() for field in row)

            # Bounds are inclusive hexadecimal code points. Keep the original
            # range text for the TSV's block column.
            bounds = code_range.split("..")
            if len(bounds) != 2:
                raise ValueError(f"{path}:{reader.line_num}: invalid block range")
            start, end = (int(bound, 16) for bound in bounds)
            if not name or not 0 <= start <= end <= MAX_CODE_POINT:
                raise ValueError(f"{path}:{reader.line_num}: invalid block")

            # Overlapping blocks would export the same code point more than once.
            if blocks and start <= blocks[-1].end:
                raise ValueError(
                    f"{path}:{reader.line_num}: overlapping or unsorted blocks"
                )
            blocks.append(UnicodeBlock(code_range, name, start, end))

    if not blocks:
        raise ValueError(f"{path}: no blocks found")
    return blocks


def read_unicode_names(path: Path) -> dict[int, str]:
    """Read explicit UnicodeData records and apply the notebook's name casing."""
    names = {}
    with path.open(encoding="utf-8", newline="") as source:
        # UnicodeData has 15 unquoted fields; the first two are code point and name.
        reader = csv.reader(source, delimiter=";", quoting=csv.QUOTE_NONE)
        for row in reader:
            if not row:
                continue
            if len(row) != UNICODE_DATA_FIELD_COUNT:
                raise ValueError(
                    f"{path}:{reader.line_num}: "
                    f"expected {UNICODE_DATA_FIELD_COUNT} UnicodeData fields"
                )
            point = int(row[0], 16)
            if not 0 <= point <= MAX_CODE_POINT:
                raise ValueError(f"{path}:{reader.line_num}: invalid code point")

            # Surrogates cannot be written as UTF-8 symbols. Their block files
            # still receive a header, but contain no character rows.
            if SURROGATE_START <= point <= SURROGATE_END:
                continue
            if point in names:
                raise ValueError(f"{path}:{reader.line_num}: duplicate code point")

            # Preserve the notebook's sentence casing, including placeholder
            # names such as <control> and the unexpanded First/Last markers.
            names[point] = row[1].capitalize()

    if not names:
        raise ValueError(f"{path}: no encodable Unicode records found")
    return names


def write_block(path: Path, entries: Iterable[UnicodeEntry]) -> None:
    """Write one UTF-8 block TSV with the standard header and CSV quoting."""
    # csv.writer uses the stream without owning it; manage the stream's lifetime.
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.writer(target, delimiter="\t", lineterminator="\n")
        writer.writerow(UnicodeEntry._fields)
        writer.writerows(entries)


def export_ucd(source_dir: Path = UCD_DIR, output_dir: Path = ICON_DIR) -> int:
    """Generate the block TSVs and remove obsolete files with generated names."""
    blocks = read_blocks(source_dir / BLOCKS_FILENAME)
    names = read_unicode_names(source_dir / UNICODE_DATA_FILENAME)
    points = sorted(names)
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    with TemporaryDirectory(prefix=".ucd-export-", dir=output_dir.parent) as temporary:
        staging = Path(temporary)
        for block in blocks:
            entries = (
                UnicodeEntry(
                    code_point=f"U+{point:04X}",
                    symbol=chr(point),
                    block=block.code_range,
                    block_name=block.name,
                    name=names[point],
                )
                for point in points[
                    bisect_left(points, block.start) : bisect_right(points, block.end)
                ]
            )
            write_block(staging / block.filename, entries)

        # Finish generating every file before replacing existing exports.
        generated = {block.filename for block in blocks}
        for name in sorted(generated):
            (staging / name).replace(output_dir / name)
        for path in output_dir.glob("*.tsv"):
            if BLOCK_FILENAME.fullmatch(path.name) and path.name not in generated:
                path.unlink()

    return len(blocks)


def main() -> None:
    """Export the locally imported UCD using paths independent of the cwd."""
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
        help="destination directory (default: %(default)s)",
    )
    args = parser.parse_args()
    try:
        count = export_ucd(args.source_dir, args.output_dir)
    except (OSError, ValueError, csv.Error) as error:
        parser.exit(1, f"error: {error}\n")
    print(f"Exported {count} Unicode blocks to {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()

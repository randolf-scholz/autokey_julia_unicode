#!/usr/bin/env python3
"""Validate TSVs against a schema without modifying them.

Usage: python src/validate_tsv.py [--schema SCHEMA.toml] [--check-icons] FILE.tsv ...
Inputs may be file paths, directories, or quoted glob patterns, including **.
Directories select their immediate *.tsv files. Each input must select a file.
Only standard-library modules are required. Header order is unrestricted.
Icon tables always check Unicode scalars and the chars/code_points relationship.
With --check-icons, also check names against icons/unicode.tsv, ignoring case.
All readable rows and matched files are checked; every error is printed.
Successful validation is silent unless --verbose prints row and file statistics.
"""

import argparse
import csv
import glob
import re
import sys
import tomllib
from collections.abc import Generator, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "icons" / "schema.toml"
UNICODE_TSV = ROOT / "icons" / "unicode.tsv"


@dataclass(frozen=True)
class Error:
    """A validation diagnostic."""

    message: str

    def __str__(self) -> str:
        return self.message


@dataclass
class ValidationStats:
    """Row counts updated as a file's validation iterator is consumed."""

    rows_validated: int = 0
    rows_total: int = 0


@dataclass(frozen=True)
class TSVFormat:
    """The schema's [format] table."""

    required_columns: list[str]
    encoding: str
    delimiter: str
    line_terminator: str
    header: bool
    allow_unknown_columns: bool
    quoting: Literal["minimal", "none"] = "minimal"
    quotechar: str | None = '"'
    doublequote: bool = True


@dataclass(frozen=True)
class ColumnSpec:
    """One [columns.<name>] table, with defaults for optional constraints."""

    allow_empty: bool
    description: str
    item_pattern: str
    list_separator: str | None = None
    min_items: int = 0
    unique_items: bool = False
    examples: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TSVSchema:
    """The TOML schema and the reader configured by its format."""

    schema_version: int
    status: str
    format: TSVFormat
    columns: dict[str, ColumnSpec]

    @classmethod
    def from_spec(cls, path: Path = SCHEMA_PATH) -> "TSVSchema":
        """Load the schema and require unique, defined required column names."""
        with Path(path).open("rb") as source:
            data = tomllib.load(source)
        try:
            fmt = TSVFormat(**data["format"])
            columns = {
                name: ColumnSpec(**column) for name, column in data["columns"].items()
            }
            schema = cls(
                schema_version=data["schema_version"],
                status=data["status"],
                format=fmt,
                columns=columns,
            )
        except (KeyError, TypeError) as error:
            raise ValueError(f"{path}: invalid schema: {error}") from error

        required = fmt.required_columns
        if len(required) != len(set(required)) or not set(required) <= columns.keys():
            raise ValueError(
                f"{path}: required_columns must list unique, defined columns"
            )

        if fmt.quoting not in ("minimal", "none"):
            raise ValueError(f"{path}: unsupported format.quoting")
        # csv.reader recognizes CR/LF record boundaries, ignoring lineterminator.
        if fmt.line_terminator not in ("\n", "\r", "\r\n"):
            raise ValueError(f"{path}: unsupported format.line_terminator")

        for name, column in columns.items():
            for key in ("item_pattern", "list_separator"):
                value = getattr(column, key)
                if key == "list_separator" and value is None:
                    continue
                if not isinstance(value, str) or not value:
                    raise ValueError(
                        f"{path}: columns.{name}.{key} must be a nonempty string"
                    )
            if column.list_separator is None and (
                {"min_items", "unique_items"} & data["columns"][name].keys()
            ):
                raise ValueError(
                    f"{path}: columns.{name}: list constraints require list_separator"
                )

        return schema

    @contextmanager
    def open_tsv(self, path: Path) -> Generator[csv.DictReader, None, None]:
        """Read using the schema's delimiter, encoding, and quoting convention."""
        fmt = self.format
        fieldnames = None if fmt.header else fmt.required_columns
        with path.open(encoding=fmt.encoding, newline="") as source:
            reader = csv.DictReader(
                source,
                fieldnames=fieldnames,
                delimiter=fmt.delimiter,
                quoting=csv.QUOTE_NONE if fmt.quoting == "none" else csv.QUOTE_MINIMAL,
                quotechar=None if fmt.quoting == "none" else fmt.quotechar,
                doublequote=fmt.doublequote,
                strict=True,
            )
            try:
                yield reader
            except UnicodeDecodeError as error:
                raise ValueError(f"{path}: invalid {fmt.encoding.upper()}") from error
            except csv.Error as error:
                raise ValueError(
                    f"{path}:{reader.reader.line_num}: invalid TSV: {error}"
                ) from error

    def validate_header(self, header: Sequence[str] | None) -> Sequence[str]:
        """Require unique headers and mandatory columns; allow extras per format."""
        if not header:
            raise ValueError("empty missing header")
        if len(header) != len(set(header)):
            raise ValueError("duplicate header")

        if missing := [
            name for name in self.format.required_columns if name not in header
        ]:
            raise ValueError(f"missing required columns: {', '.join(missing)}")

        unknown = set(header) - self.columns.keys()
        if unknown and not self.format.allow_unknown_columns:
            raise ValueError(f"unknown columns: {', '.join(sorted(unknown))}")
        return header


@dataclass(frozen=True)
class Icon:
    """Known icon fields, with numeric code points and scalar text values."""

    code_points: list[int]
    chars: str
    tab_completions: list[str]
    unicode_name: str

    @classmethod
    def from_row(cls, parsed: dict[str, list[str]]) -> "Icon":
        """Convert schema-validated field items into the known icon types."""
        return cls(
            code_points=[
                int(value.removeprefix("U+"), 16) for value in parsed["code_points"]
            ],
            chars="".join(parsed["chars"]),
            tab_completions=parsed["tab_completions"],
            unicode_name="".join(parsed["unicode_name"]),
        )


class FieldValidator:
    """Parse a field and validate its items using the schema's constraints."""

    def __init__(self, column: ColumnSpec) -> None:
        self.column = column
        self.pattern = re.compile(column.item_pattern)

    def parse(self, value: str) -> list[str]:
        """Split a field without validating it; an empty cell has no items."""
        if not value:
            return []
        separator = self.column.list_separator
        return [value] if separator is None else value.split(separator)

    def validate(self, value: str, *, context: str) -> list[str]:
        """Return the validated items; an allowed empty cell has no items."""
        column = self.column
        if not value:
            if not column.allow_empty:
                raise ValueError(f"{context}: must not be empty")
            return []

        items = self.parse(value)
        if column.list_separator is not None:
            if not column.allow_empty and "" in items:
                raise ValueError(f"{context}: empty list item")
            if len(items) < column.min_items:
                raise ValueError(f"{context}: too few list items")
            if column.unique_items and len(items) != len(set(items)):
                raise ValueError(f"{context}: duplicate list item")

        if any(self.pattern.fullmatch(item) is None for item in items):
            raise ValueError(f"{context}: invalid item pattern")
        return items


def validate_row(
    row: dict[str | None, Any],
    validators: dict[str, FieldValidator],
    *,
    expected_fields: int,
    context: str,
) -> list[Error]:
    """Return row-width and field validation errors."""
    if None in row or None in row.values():
        missing = sum(value is None for value in row.values())
        extra = len(row.get(None, []))
        fields = expected_fields - missing + extra
        return [Error(f"{context}: expected {expected_fields} fields, got {fields}")]
    errors = []
    for name, validator in validators.items():
        if name not in row:
            continue
        try:
            validator.validate(row[name], context=f"{context}: {name}")
        except ValueError as error:
            errors.append(Error(str(error)))
    return errors


def is_variation_selector(point: int, /) -> bool:
    """Unicode variation selectors, including the supplementary range."""
    return 0xFE00 <= point <= 0xFE0F or 0xE0100 <= point <= 0xE01EF


def is_name_modifier(point: int, /) -> bool:
    """A trailing combining mark or variation selector that uses the base name."""
    return (
        0x0300 <= point <= 0x036F  # Combining Diacritical Marks
        or 0xFE00 <= point <= 0xFE0F  # Variation Selectors
        or 0xE0100 <= point <= 0xE01EF  # Variation Selectors Supplement
    )


def validate_icon(icon: Icon, names: dict[int, str], *, context: str) -> list[Error]:
    """Check scalars and exact chars; empty chars implicitly uses code_points."""
    points = icon.code_points
    if any(not 0 <= point <= 0x10FFFF or 0xD800 <= point <= 0xDFFF for point in points):
        return [Error(f"{context}: code_points: invalid Unicode scalar value")]
    errors = []
    expected_chars = "".join(map(chr, points))
    if icon.chars and icon.chars != expected_chars:
        errors.append(Error(f"{context}: chars: does not match code_points"))
    if len(points) == 1 or (len(points) == 2 and is_variation_selector(points[1])):
        expected = names.get(points[0])
        if expected is not None and icon.unicode_name.lower() != expected.lower():
            errors.append(Error(f"{context}: unicode_name: expected {expected!r}"))
    return errors


def validate_tsv(
    path: Path,
    *,
    schema_path: Path = SCHEMA_PATH,
    check_icons: bool = False,
    unicode_tsv: Path = UNICODE_TSV,
    stats: ValidationStats | None = None,
) -> Iterator[Error]:
    """Yield diagnostics for all readable rows without printing or raising them.

    If supplied, stats counts valid and total rows as the iterator is consumed.
    An unreadable file or schema prevents further validation of that file.

    Icon tables always check Unicode scalar values and exact chars/code_points
    equality, including variation selectors. With check_icons, check names against
    unicode_tsv, ignoring case and one optional trailing variation selector.
    Skip names for other sequences and characters absent from the table.
    Never strip or normalize chars.
    """
    path = Path(path)
    if stats is None:
        stats = ValidationStats()
    try:
        schema = TSVSchema.from_spec(schema_path)
        validators = {
            name: FieldValidator(column) for name, column in schema.columns.items()
        }
    except (ValueError, OSError, re.error) as error:
        yield Error(str(error))
        return
    icon_columns = {"code_points", "chars", "tab_completions", "unicode_name"}

    names: dict[int, str] = {}
    if check_icons:
        try:
            with TSVSchema.from_spec().open_tsv(unicode_tsv) as reader:
                names = {
                    int(row["code_points"].removeprefix("U+"), 16): row["unicode_name"]
                    for row in reader
                }
        except (ValueError, OSError) as error:
            yield Error(str(error))
        except KeyError as error:
            yield Error(f"{unicode_tsv}: missing required column: {error}")

    try:
        with schema.open_tsv(path) as reader:
            header = reader.fieldnames
            try:
                schema.validate_header(header)
            except ValueError as error:
                yield Error(f"{path}:1: {error}")
            while True:
                try:
                    row = next(reader)
                except StopIteration:
                    break
                except csv.Error as error:
                    stats.rows_total += 1
                    yield Error(
                        f"{path}:{reader.reader.line_num}: invalid TSV: {error}"
                    )
                    continue
                stats.rows_total += 1
                context = f"{path}:{reader.line_num}"
                errors = validate_row(
                    row,
                    validators,
                    expected_fields=len(header or []),
                    context=context,
                )
                if not errors and icon_columns <= row.keys():
                    parsed = {
                        name: validator.parse(row[name])
                        for name, validator in validators.items()
                        if name in row
                    }
                    errors.extend(
                        validate_icon(Icon.from_row(parsed), names, context=context)
                    )
                if not errors:
                    stats.rows_validated += 1
                yield from errors
    except (ValueError, OSError) as error:
        yield Error(str(error))


def expand_files(patterns: Sequence[str]) -> Iterator[Path | Error]:
    """Yield files or input errors, continuing after invalid inputs.

    Directories select immediate *.tsv files; globs support recursive **.
    Existing literal paths take precedence over glob syntax in their names.
    """
    for pattern in patterns:
        try:
            path = Path(pattern)
            matches = (
                [path]
                if path.exists()
                else sorted(map(Path, glob.glob(pattern, recursive=True)))
            )
            files = []
            for match in matches:
                if match.is_dir():
                    files.extend(
                        file for file in sorted(match.glob("*.tsv")) if file.is_file()
                    )
                else:
                    files.append(match)
            if files:
                yield from files
            else:
                yield Error(f"No files match: {pattern}")
        except OSError as error:
            yield Error(str(error))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "files", nargs="+", help="file paths, directories, or glob patterns"
    )
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="print per-file row counts and file totals",
    )
    parser.add_argument(
        "--check-icons",
        action="store_true",
        help="also validate icon names against the Unicode names table",
    )
    parser.add_argument(
        "--unicode-tsv",
        type=Path,
        default=UNICODE_TSV,
        help="Unicode names table used with --check-icons",
    )
    args = parser.parse_args()
    error_count = 0
    files_validated = 0
    files_total = 0
    for path in expand_files(args.files):
        if isinstance(path, Error):
            print(path, file=sys.stderr)
            error_count += 1
            continue
        files_total += 1
        stats = ValidationStats()
        file_error_count = 0
        for error in validate_tsv(
            path,
            schema_path=args.schema,
            check_icons=args.check_icons,
            unicode_tsv=args.unicode_tsv,
            stats=stats,
        ):
            print(error, file=sys.stderr)
            error_count += 1
            file_error_count += 1
        if not file_error_count:
            files_validated += 1
        if args.verbose:
            print(f"{path}: {stats.rows_validated}/{stats.rows_total} rows validated")
    if args.verbose:
        print(f"{files_validated}/{files_total} files validated")
    if error_count:
        print(f"{error_count} errors found", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()

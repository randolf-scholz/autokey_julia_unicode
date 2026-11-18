#!/usr/bin/env python3
"""Import base LaTeX symbol mappings from an installed TeX distribution.

Requires the LaTeX base and unicode-math source tables, and kpsewhich unless
--source-dir is provided.
unicode-math supplies Unicode identities, not the inventory of base commands.
See data/latex/README.md for the exact coverage and encoding assumptions.
"""

import argparse
import csv
import hashlib
import re
import shutil
import subprocess
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import NamedTuple

PROJECT_DIR = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT_DIR / "data" / "latex" / "latex2e.tsv"
HEADER = ("code_points", "chars", "mode", "latex_code")

# Fragments/modifiers and extensible fills have no standalone character identity.
EXCLUDED_MATH = frozenset(
    [
        r"\not",
        r"\mapstochar",
        r"\lhook",
        r"\rhook",
        r"\braceld",
        r"\bracerd",
        r"\bracelu",
        r"\braceru",
        r"\arrowvert",
        r"\Arrowvert",
        r"\bracevert",
        r"\joinrel",
        r"\relbar",
        r"\Relbar",
        r"\rightarrowfill",
        r"\leftarrowfill",
        r"\downbracefill",
        r"\upbracefill",
    ]
)

# Explicit semantic aliases absent from unicode-math's single-symbol table.
MATH_ALIASES = {
    r"\triangle": r"\bigtriangleup",
    r"\intop": r"\int",
    r"\ointop": r"\oint",
    r"\smallint": r"\int",
    r"\varbigtriangleup": r"\bigtriangleup",
    r"\varbigtriangledown": r"\bigtriangledown",
    r"\ldotp": r"\mathperiod",
    r"\colon": r"\mathcolon",
    r"\|": r"\Vert",
    r"\iff": r"\Longleftrightarrow",
    r"\mathellipsis": r"\unicodeellipsis",
    r"\cdots": r"\unicodecdots",
}


# Fixed kernel wrappers whose meanings are explicit in latex.ltx.
KERNEL_WRAPPERS = {
    r"\$": ("$", "both"),
    r"\{": ("{", "both"),
    r"\}": ("}", "both"),
    r"\P": ("¶", "both"),
    r"\S": ("§", "both"),
    r"\dag": ("†", "both"),
    r"\ddag": ("‡", "both"),
    r"\_": ("_", "both"),
    r"\copyright": ("©", "both"),
    r"\pounds": ("£", "both"),
    r"\dots": ("…", "both"),
    r"\ldots": ("…", "both"),
    r"\%": ("%", "both"),
    r"\&": ("&", "both"),
    r"\#": ("#", "both"),
    r"\lbrack": ("[", "both"),
    r"\rbrack": ("]", "both"),
    r"\slash": ("/", "both"),
    r"\lq": ("‘", "text"),
    r"\rq": ("’", "text"),
    r"\aa": ("å", "text"),
    r"\AA": ("Å", "text"),
}


class LatexMapping(NamedTuple):
    """A LaTeX command mapping in TSV column order."""

    code_points: str
    chars: str
    mode: str
    latex_code: str


def without_comments(source: str) -> str:
    """Strip TeX comments while preserving escaped percent signs."""
    return re.sub(r"(?<!\\)((?:\\\\)*)%[^\n]*", r"\1", source)


def parse_tex_argument(source: str, offset: int) -> tuple[str, int]:
    """Read a braced group, control sequence, or single TeX token."""
    # Whitespace before an argument is not part of its value.
    while offset < len(source) and source[offset].isspace():
        offset += 1
    if offset == len(source):
        raise ValueError("Missing TeX argument")

    # Track nested groups and return the contents without the outer braces.
    start = offset
    if source[offset] == "{":
        depth = 1
        offset += 1
        while offset < len(source):
            if source[offset] == "\\":
                # A control symbol such as \{ is not a grouping brace.
                offset += 2
                continue

            if source[offset] == "{":
                depth += 1
            elif source[offset] == "}":
                depth -= 1
                if depth == 0:
                    return source[start + 1 : offset], offset + 1
            offset += 1
        raise ValueError("Unclosed TeX group")

    # An unbraced control sequence consumes a full name or one control symbol.
    if source[offset] == "\\":
        match = re.match(r"\\(?:[A-Za-z@]+|.)", source[offset:])
        if match is None:
            raise ValueError("Incomplete control sequence")
        return match[0], offset + len(match[0])

    # Any other unbraced argument is a single character.
    return source[offset], offset + 1


def iter_declaration_calls(
    source: str, name: str, count: int
) -> Iterator[tuple[str, ...]]:
    """Read literal declaration calls, skipping definitions and parameterized ones."""
    for match in re.finditer(r"\\" + name + r"\b", source):
        first, offset = parse_tex_argument(source, match.end())
        if not first.startswith("\\") or source[offset:].lstrip().startswith("["):
            continue
        values = [first]
        for _ in range(count - 1):
            value, offset = parse_tex_argument(source, offset)
            values.append(value)
        yield tuple(values)


def unicode_number(value: str) -> str:
    """Decode a hexadecimal TeX character number (not a legacy font slot)."""
    if not re.fullmatch(r'"[0-9A-Fa-f]+', value):
        raise ValueError(f"Expected Unicode character number, got {value!r}")
    point = int(value[1:], 16)
    if not 0 <= point <= 0x10FFFF or 0xD800 <= point <= 0xDFFF:
        raise ValueError(f"Not a Unicode scalar value: {value}")
    return chr(point)


def math_mappings(fontmath: str, table: str, aliases: str) -> dict[str, str]:
    """Map only standalone commands declared by fontmath.ltx."""
    # language=regexp
    pattern = r'\\UnicodeMathSymbol\{"([0-9A-F]+)\}\{(\\[A-Za-z]+)\s*\}'
    points = {name: chr(int(point, 16)) for point, name in re.findall(pattern, table)}
    # Legacy Greek names denote character identities, without adding font styling.
    for name, text in list(points.items()):
        if name.startswith(r"\mup"):
            points["\\" + name[4:]] = text
    redirects = dict(re.findall(r"\\protected\\def\s*(\\\w+)\s*\{(\\\w+)\}", aliases))
    redirects.update(MATH_ALIASES)
    for _ in range(len(redirects)):
        for name, target in redirects.items():
            if target in points:
                points[name] = points[target]
    # The kernel draws this with a rule rather than a font glyph.
    points[r"\mathunderscore"] = "_"

    # Both explicit symbols/delimiters and fixed, composed robust commands.
    commands = set(
        re.findall(r"\\DeclareMath(?:Symbol|Delimiter)\{(\\[^}]+)\}", fontmath)
    )
    commands.update(
        re.findall(r"\\DeclareRobustCommand\s*(\\[A-Za-z]+)\s*(?=\{)", fontmath)
    )
    result = {}
    for name in sorted(commands - EXCLUDED_MATH):
        if name not in points:
            raise ValueError(f"No Unicode mapping for base math command {name}")
        result[name] = points[name]
    return result


def text_mappings(tuenc: str) -> dict[str, str]:
    """Read Unicode symbols, fixed commands, and explicitly declared composites."""
    result = {
        name: unicode_number(value)
        for name, value in iter_declaration_calls(tuenc, "DeclareUnicodeSymbol", 2)
    }
    for name, body in iter_declaration_calls(tuenc, "DeclareUnicodeCommand", 2):
        # Fixed commands use a Unicode slot directly or test it before a fallback.
        value = re.search(r'"[0-9A-Fa-f]+', body)
        if value is None:
            raise ValueError(f"No Unicode slot for text command {name}")
        result[name] = unicode_number(value[0])
    for accent, base, value in iter_declaration_calls(
        tuenc, "DeclareUnicodeComposite", 3
    ):
        result[f"{accent}{{{base}}}"] = unicode_number(value)
    return result


def kernel_aliases(kernel: str, math: dict[str, str], text: dict[str, str]) -> None:
    """Add fixed kernel wrappers whose meanings are explicit in latex.ltx."""
    # Modern textcomp support has additional direct Unicode declarations here.
    pattern = (
        # language=regexp
        r'\\DeclareTextSymbol\s*\{(\\[^}]+)\}\s*\\UnicodeEncodingName\s*\{("[0-9A-F]+)\}'
    )
    for name, value in re.findall(pattern, kernel):
        text[name] = unicode_number(value)
    for name, (value, mode) in KERNEL_WRAPPERS.items():
        # Guard against applying the curated mappings to a different kernel API.
        if name not in kernel:
            raise ValueError(f"Kernel no longer contains {name}")
        if mode == "both":
            math[name] = value
        text[name] = value


def merge_math_and_text_mappings(
    math: dict[str, str], text: dict[str, str]
) -> Iterator[LatexMapping]:
    """Merge identical mappings across modes and retain all command aliases."""
    for name in sorted(math.keys() | text.keys()):
        if name in math and name in text and math[name] == text[name]:
            values = [("both", math[name])]
        else:
            values = [
                (mode, values[name])
                for mode, values in (("math", math), ("text", text))
                if name in values
            ]
        for mode, value in values:
            points = ", ".join(f"U+{ord(char):04X}" for char in value)
            yield LatexMapping(points, value, mode, name)


def import_latex(output: Path = OUTPUT, *, source_dir: Path | None = None) -> int:
    """Generate a deterministic UTF-8 TSV from local or installed TeX sources."""
    # Resolve installed sources only when no explicit source directory is given.
    executable = shutil.which("kpsewhich") if source_dir is None else None

    sources = {}
    for filename in (
        "fontmath.ltx",
        "tuenc.def",
        "latex.ltx",
        "unicode-math-table.tex",
        "unicode-math-luatex.sty",
    ):
        if source_dir is not None:
            source = source_dir / filename
        else:
            if executable is None:
                raise FileNotFoundError("kpsewhich executable not found on PATH")
            # The executable and source filenames are controlled by this importer.
            location = subprocess.check_output(  # noqa: S603
                [executable, filename], text=True
            ).strip()
            if not location:
                raise FileNotFoundError(f"kpsewhich could not find {filename}")
            source = Path(location)

        # Report hashes of the original sources before stripping TeX comments.
        raw = source.read_bytes()
        print(f"{filename}: SHA256 {hashlib.sha256(raw).hexdigest()}")
        sources[filename] = without_comments(raw.decode("utf-8"))

    # Build each mode's inventory, then add the fixed kernel aliases.
    math = math_mappings(
        sources["fontmath.ltx"],
        sources["unicode-math-table.tex"],
        sources["unicode-math-luatex.sty"],
    )
    text = text_mappings(sources["tuenc.def"])
    kernel_aliases(sources["latex.ltx"], math, text)

    # Merge shared mappings and sort by Unicode sequence, command, then mode.
    entries = sorted(
        merge_math_and_text_mappings(math, text),
        key=lambda row: (tuple(map(ord, row.chars)), row.latex_code, row.mode),
    )

    # Write a reproducible TSV with explicit UTF-8 encoding and LF line endings.
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as target:
        writer = csv.writer(target, delimiter="\t", lineterminator="\n")
        writer.writerow(HEADER)
        writer.writerows(entries)

    return len(entries)


def main(argv: Sequence[str] | None = None) -> int:
    """Import LaTeX mappings into a TSV using command-line options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument(
        "--source-dir",
        type=Path,
        help="Read TeX sources here instead of using kpsewhich",
    )
    args = parser.parse_args(argv)
    count = import_latex(args.output, source_dir=args.source_dir)
    print(f"Imported {count} mappings to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

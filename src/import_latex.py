#!/usr/bin/env python3
"""Import base LaTeX symbol mappings from an installed TeX distribution.

Requires kpsewhich and the LaTeX base and unicode-math source tables.
unicode-math supplies Unicode identities, not the inventory of base commands.
See latex/README.md for the exact coverage and encoding assumptions.
"""

import argparse
import csv
import hashlib
import re
import subprocess
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT_DIR / "latex" / "latex2e.tsv"
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


def without_comments(source: str) -> str:
    """Strip TeX comments while preserving escaped percent signs."""
    return re.sub(r"(?<!\\)((?:\\\\)*)%[^\n]*", r"\1", source)


def argument(source: str, offset: int) -> tuple[str, int]:
    """Read a braced group, control sequence, or single TeX token."""
    while offset < len(source) and source[offset].isspace():
        offset += 1
    if offset == len(source):
        raise ValueError("Missing TeX argument")
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
    if source[offset] == "\\":
        match = re.match(r"\\(?:[A-Za-z@]+|.)", source[offset:])
        if match is None:
            raise ValueError("Incomplete control sequence")
        return match[0], offset + len(match[0])
    return source[offset], offset + 1


def calls(source: str, name: str, count: int):
    """Read literal declaration calls, skipping definitions and parameterized ones."""
    for match in re.finditer(r"\\" + name + r"\b", source):
        first, offset = argument(source, match.end())
        if not first.startswith("\\") or source[offset:].lstrip().startswith("["):
            continue
        values = [first]
        for _ in range(count - 1):
            value, offset = argument(source, offset)
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
    points = {
        name: chr(int(point, 16))
        for point, name in re.findall(
            r'\\UnicodeMathSymbol\{"([0-9A-F]+)\}\{(\\[A-Za-z]+)\s*\}', table
        )
    }
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
        for name, value in calls(tuenc, "DeclareUnicodeSymbol", 2)
    }
    for name, body in calls(tuenc, "DeclareUnicodeCommand", 2):
        # Fixed commands use a Unicode slot directly or test it before a fallback.
        value = re.search(r'"[0-9A-Fa-f]+', body)
        if value is None:
            raise ValueError(f"No Unicode slot for text command {name}")
        result[name] = unicode_number(value[0])
    for accent, base, value in calls(tuenc, "DeclareUnicodeComposite", 3):
        result[f"{accent}{{{base}}}"] = unicode_number(value)
    return result


def kernel_aliases(kernel: str, math: dict[str, str], text: dict[str, str]) -> None:
    """Add fixed kernel wrappers whose meanings are explicit in latex.ltx."""
    # Modern textcomp support has additional direct Unicode declarations here.
    for name, value in re.findall(
        r'\\DeclareTextSymbol\s*\{(\\[^}]+)\}\s*\\UnicodeEncodingName\s*\{("[0-9A-F]+)\}',
        kernel,
    ):
        text[name] = unicode_number(value)
    wrappers = {
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
    for name, (value, mode) in wrappers.items():
        # Guard against applying the curated mappings to a different kernel API.
        if name not in kernel:
            raise ValueError(f"Kernel no longer contains {name}")
        if mode == "both":
            math[name] = value
        text[name] = value


def rows(math: dict[str, str], text: dict[str, str]):
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
            yield points, value, mode, name


def import_latex(output: Path = OUTPUT) -> int:
    """Locate installed sources and generate a deterministic UTF-8 TSV."""
    sources = {}
    for filename in (
        "fontmath.ltx",
        "tuenc.def",
        "latex.ltx",
        "unicode-math-table.tex",
        "unicode-math-luatex.sty",
    ):
        location = subprocess.check_output(["kpsewhich", filename], text=True).strip()
        if not location:
            raise FileNotFoundError(f"kpsewhich could not find {filename}")
        raw = Path(location).read_bytes()
        print(f"{filename}: SHA256 {hashlib.sha256(raw).hexdigest()}")
        sources[filename] = without_comments(raw.decode("utf-8"))
    math = math_mappings(
        sources["fontmath.ltx"],
        sources["unicode-math-table.tex"],
        sources["unicode-math-luatex.sty"],
    )
    text = text_mappings(sources["tuenc.def"])
    kernel_aliases(sources["latex.ltx"], math, text)
    entries = sorted(
        rows(math, text),
        key=lambda row: (tuple(map(ord, row[1])), row[3], row[2]),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as target:
        writer = csv.writer(target, delimiter="\t", lineterminator="\n")
        writer.writerow(HEADER)
        writer.writerows(entries)
    return len(entries)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(f"Imported {import_latex(args.output)} mappings to {args.output}")


if __name__ == "__main__":
    main()

"""Check LaTeX command inventory, Unicode identities, and text/math modes."""

import csv
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from src import import_latex as latex
from src.import_latex import (
    math_mappings,
    merge_math_and_text_mappings,
    parse_tex_argument,
    text_mappings,
    unicode_number,
    without_comments,
)
from src.validate_tsv import validate_tsv

ROOT = Path(__file__).resolve().parents[1]
LATEX_SCHEMA = ROOT / "data/schemas/latex.toml"
TEX_SOURCES = {
    "fontmath.ltx": r"""
        \DeclareMathSymbol{\testmath}{\mathord}{letters}{"00}
        \DeclareMathSymbol{\shared}{\mathord}{letters}{"01}
    """,
    "unicode-math-table.tex": r"""
        \UnicodeMathSymbol{"003B1}{\testmath}{\mathalpha}{test math}
        \UnicodeMathSymbol{"02605}{\shared}{\mathord}{shared symbol}
    """,
    "tuenc.def": r"""
        \DeclareUnicodeSymbol{\testtext}{"03B2}
        \DeclareUnicodeSymbol{\shared}{"2605}
        \DeclareUnicodeComposite{\"}{a}{"00E4}
    """,
    "latex.ltx": r"""
        \$ \{ \} \P \S \dag \ddag \_ \copyright \pounds \dots \ldots
        \% \& \# \lbrack \rbrack \slash \lq \rq \aa \AA
    """,
    "unicode-math-luatex.sty": "",
}


def test_math_inventory_comes_from_base_not_unicode_math() -> None:
    declarations = r"""
    \DeclareMathSymbol{\alpha}{\mathord}{letters}{"0B}
    \DeclareMathSymbol{\epsilon}{\mathord}{letters}{"0F}
    \DeclareMathSymbol{\varepsilon}{\mathord}{letters}{"22}
    \DeclareMathSymbol{\intop}{\mathop}{largesymbols}{"52}
    \DeclareMathSymbol{\not}{\mathrel}{symbols}{"36}
    \DeclareRobustCommand\sqrt[1]{#1}
    """
    table = r"""
    \UnicodeMathSymbol{"003B1}{\mupalpha}{\mathalpha}{alpha}
    \UnicodeMathSymbol{"003F5}{\mupepsilon}{\mathalpha}{epsilon}
    \UnicodeMathSymbol{"003B5}{\mupvarepsilon}{\mathalpha}{varepsilon}
    \UnicodeMathSymbol{"0222B}{\int}{\mathop}{integral}
    \UnicodeMathSymbol{"02204}{\nexists}{\mathord}{not exists}
    """
    expected = {
        r"\alpha": "α",
        r"\epsilon": "ϵ",
        r"\varepsilon": "ε",
        r"\intop": "∫",
    }
    assert math_mappings(declarations, table, "") == expected


def test_unknown_math_command_is_not_silently_omitted() -> None:
    with pytest.raises(ValueError, match="No Unicode mapping"):
        math_mappings(r'\DeclareMathSymbol{\new}{\mathord}{letters}{"01}', "", "")


def test_text_symbols_fallbacks_and_accent_composites() -> None:
    source = without_comments(r"""
    % \DeclareUnicodeSymbol{\notreal}{"0000}
    \def\DeclareUnicodeSymbol#1{\DeclareTextSymbol{#1}{TU}}
    \DeclareUnicodeSymbol{\textdollar}{"0024}
    \DeclareUnicodeCommand\textfiguredash
        {\iffontchar\font "2012 \char "2012 \else \char "2013 \fi}
    \DeclareUnicodeCommand\textcommabelow[1]{#1}
    \DeclareUnicodeAccent{\"}{"0308}
    \DeclareUnicodeComposite{\"}{a}{"00E4}
    \DeclareUnicodeComposite{\'}\ae{"01FD}
    """)
    expected = {
        r"\textdollar": "$",
        r"\textfiguredash": "‒",
        r"\"{a}": "ä",
        r"\'{\ae}": "ǽ",
    }
    assert text_mappings(source) == expected


def test_comments_and_escaped_group_characters() -> None:
    assert without_comments("a% hidden\nb\\%c") == "a\nb\\%c"
    assert parse_tex_argument(r"{\{x\} {y}}", 0)[0] == r"\{x\} {y}"


def test_modes_merge_only_when_unicode_sequences_agree() -> None:
    actual = list(
        merge_math_and_text_mappings(
            {r"\a": "α", r"\b": "β"},
            {r"\a": "α", r"\b": "b\u0338"},
        )
    )
    expected = [
        ("U+03B1", "α", "both", r"\a"),
        ("U+03B2", "β", "math", r"\b"),
        ("U+0062, U+0338", "b\u0338", "text", r"\b"),
    ]
    assert actual == expected


@pytest.mark.parametrize("value", ['"D800', '"110000', "11", "`a"])
def test_unicode_number_rejects_surrogates_and_legacy_slots(value: str) -> None:
    with pytest.raises(ValueError, match=r"Unicode (character number|scalar value)"):
        unicode_number(value)


def test_import_writes_schema_compliant_mappings() -> None:
    with TemporaryDirectory() as tmpdir:
        # Supply local TeX sources so the test needs no installed distribution.
        directory = Path(tmpdir)
        sources = directory / "tex"
        sources.mkdir()
        for name, contents in TEX_SOURCES.items():
            (sources / name).write_text(contents)

        # Exercise the CLI and verify that repeated imports produce identical bytes.
        output = directory / "export.tsv"
        args = ["--source-dir", str(sources), "--output", str(output)]
        assert latex.main(args) == 0
        first_export = output.read_bytes()
        assert latex.main(args) == 0
        assert output.read_bytes() == first_export

        # Validate the TSV schema before inspecting individual mappings.
        assert list(validate_tsv(output, schema_path=LATEX_SCHEMA)) == []
        with output.open(encoding="utf8", newline="") as source:
            entries = list(csv.DictReader(source, delimiter="\t"))

        # Each command and mode pair must identify a unique mapping.
        mappings = {
            (entry["latex_code"], entry["mode"]): entry["chars"] for entry in entries
        }
        assert len(mappings) == len(entries)

        for entry in entries:
            # The serialized code points must reproduce the character sequence.
            decoded_chars = "".join(
                chr(int(p.removeprefix("U+"), 16))
                for p in entry["code_points"].split(", ")
            )
            assert decoded_chars == entry["chars"]

            # A shared mapping replaces the separate math and text entries.
            if entry["mode"] == "both":
                assert (entry["latex_code"], "text") not in mappings
                assert (entry["latex_code"], "math") not in mappings

        # Check representative mode-specific, shared, and accent mappings.
        assert mappings[r"\testmath", "math"] == "α"
        assert mappings[r"\testtext", "text"] == "β"
        assert mappings[r"\shared", "both"] == "★"
        assert mappings[r"\"{a}", "text"] == "ä"

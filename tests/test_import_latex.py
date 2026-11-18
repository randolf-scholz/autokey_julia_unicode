"""Check LaTeX command inventory, Unicode identities, and text/math modes."""

import csv
from pathlib import Path

import pytest
from src.import_latex import (
    argument,
    math_mappings,
    rows,
    text_mappings,
    unicode_number,
    without_comments,
)
from src.validate_tsv import validate_tsv

ROOT = Path(__file__).resolve().parents[1]


def test_math_inventory_comes_from_base_not_unicode_math():
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
    assert math_mappings(declarations, table, "") == {
        r"\alpha": "α",
        r"\epsilon": "ϵ",
        r"\varepsilon": "ε",
        r"\intop": "∫",
    }


def test_unknown_math_command_is_not_silently_omitted():
    with pytest.raises(ValueError, match="No Unicode mapping"):
        math_mappings(r'\DeclareMathSymbol{\new}{\mathord}{letters}{"01}', "", "")


def test_text_symbols_fallbacks_and_accent_composites():
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
    assert text_mappings(source) == {
        r"\textdollar": "$",
        r"\textfiguredash": "‒",
        r"\"{a}": "ä",
        r"\'{\ae}": "ǽ",
    }


def test_comments_and_escaped_group_characters():
    assert without_comments("a% hidden\nb\\%c") == "a\nb\\%c"
    assert argument(r"{\{x\} {y}}", 0)[0] == r"\{x\} {y}"


def test_modes_merge_only_when_unicode_sequences_agree():
    assert list(rows({r"\a": "α", r"\b": "β"}, {r"\a": "α", r"\b": "b\u0338"})) == [
        ("U+03B1", "α", "both", r"\a"),
        ("U+03B2", "β", "math", r"\b"),
        ("U+0062, U+0338", "b\u0338", "text", r"\b"),
    ]


@pytest.mark.parametrize("value", ['"D800', '"110000', "11", "`a"])
def test_unicode_number_rejects_surrogates_and_legacy_slots(value: str):
    with pytest.raises(ValueError):
        unicode_number(value)


def test_bundled_table_matches_schema_and_known_symbol_identities():
    path = ROOT / "data/latex/latex2e.tsv"
    assert list(validate_tsv(path, schema_path=ROOT / "data/schemas/latex.toml")) == []
    with path.open(encoding="utf8", newline="") as source:
        entries = list(csv.DictReader(source, delimiter="\t"))
    mappings = {
        (entry["latex_code"], entry["mode"]): entry["chars"] for entry in entries
    }
    assert len(mappings) == len(entries)
    for entry in entries:
        assert (
            "".join(
                chr(int(p.removeprefix("U+"), 16))
                for p in entry["code_points"].split(", ")
            )
            == entry["chars"]
        )
        if entry["mode"] == "both":
            assert (entry["latex_code"], "text") not in mappings
            assert (entry["latex_code"], "math") not in mappings
    for code, text in [
        (r"\epsilon", "ϵ"),
        (r"\varepsilon", "ε"),
        (r"\phi", "ϕ"),
        (r"\varphi", "φ"),
    ]:
        assert mappings[code, "math"] == text
    assert mappings[r"\"{a}", "text"] == "ä"
    assert (r"\nexists", "math") not in mappings

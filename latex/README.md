# LaTeX Unicode mappings

Each TSV describes one LaTeX package context. Rows map complete LaTeX expressions
to Unicode sequences; the package context belongs to the file rather than being
repeated in every row. Different packages may define the same command differently.
The reverse index, from Unicode sequences to available LaTeX expressions, can be
derived by joining on `code_points`.

[`schema.toml`](schema.toml) defines the columns and serialization. It reuses
[`../icons/schema-definition.json`](../icons/schema-definition.json) to validate
the column definitions with Tombi.

| Column        | Required | Meaning                                                   |
|---------------|----------|-----------------------------------------------------------|
| `code_points` | Yes      | Nonempty comma-space-separated Unicode scalar sequence    |
| `text`        | No       | The decoded Unicode sequence, included for readability    |
| `mode`        | Yes      | `math`, `text`, or `both`                                 |
| `latex_code`  | Yes      | A complete command or expression, without math delimiters |

The `(latex_code, mode)` pair must be unique. A `both` row means the same mapping
works in both modes; it must not coexist with a `math` or `text` row for that
expression. Command aliases remain separate rows. TSV fields use double-quote
escaping, so an accent expression such as `\"{a}` must be read with a TSV/CSV
parser rather than by splitting lines and tabs manually.

[`latex2e.tsv`](latex2e.tsv) currently contains **635 mappings**: 223 math-only,
394 text-only, and 18 valid in both modes. Its context is the LaTeX2e kernel,
without any additional symbol package. Text mappings use the kernel's Unicode
text encoding (`TU`), as used by LuaLaTeX and XeLaTeX. Legacy pdfLaTeX text
encodings can produce different glyphs, need font-encoding setup, or lack symbols.
Availability of a command does not guarantee that the selected font has its glyph.
Mappings preserve character identity, not TeX's spacing, sizing, or font metrics.

The table includes all named standalone symbol and delimiter declarations in
`fontmath.ltx`, its fixed composed symbols such as `\notin` and `\longmapsto`,
the explicit Unicode symbols and accent composites in `tuenc.def`, and selected
kernel aliases and additional direct Unicode text declarations in `latex.ltx`.
For example, `\epsilon` maps to U+03F5 and `\varepsilon` to U+03B5; `\phi`
maps to U+03D5 and `\varphi` to U+03C6. These are distinct character identities.

This is a generated symbol inventory, **not an exhaustive list of all base LaTeX
commands or possible expressions**. It excludes:

- Commands requiring arbitrary arguments, such as `\frac`, `\sqrt`, `\hat`,
  and font-selection commands. Only explicitly declared, complete accent
  expressions such as `\"{a}` are enumerated.
- Layout, spacing, and named textual operator commands, such as `\section`,
  `\quad`, and `\sin`, and logos such as `\LaTeX`.
- Glyph fragments and construction helpers, including `\not`, `\mapstochar`,
  `\lhook`, `\rhook`, brace pieces, `\arrowvert`, `\Arrowvert`, `\bracevert`,
  `\joinrel`, `\relbar`, `\Relbar`, and extensible arrow/brace fills. Complete
  commands using those pieces are included when they have a Unicode identity.
- Remaining TS1-only shapes and font variants without an explicit Unicode
  declaration in the sources above, such as `\textleaf`, `\textcopyleft`,
  and oldstyle-digit commands. These need a separate mapping audit.
- Symbols provided only by packages, such as `\nexists` from `amssymb`.

The sources are from the local **TeX Live 2026** installation, with kernel **LaTeX2e 2026-06-01**, `fontmath.ltx`
**2025/06/05 v3.0l**, and `tuenc.def`
**2025/07/18 v2.1d**. The mapping reference is `unicode-math` **2023/08/13 v0.8r**.
Files are located using `kpsewhich`, so regeneration does not depend on a
particular installation path.

| Installed source          | Upstream source                                                                                                                          | Use                                                                                    |
|---------------------------|------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------|
| `fontmath.ltx`            | [LaTeX2e `fontdef.dtx`](https://github.com/latex3/latex2e/blob/main/base/fontdef.dtx)                                                    | Base math command inventory; its hexadecimal values are legacy font slots, not Unicode |
| `tuenc.def`               | [LaTeX2e `ltoutenc.dtx`](https://github.com/latex3/latex2e/blob/main/base/ltoutenc.dtx)                                                  | Explicit Unicode text symbols, fixed commands, and accent composites                   |
| `latex.ltx`               | [LaTeX2e base sources](https://github.com/latex3/latex2e/tree/main/base), especially `ltoutenc.dtx`, `ltplain.dtx`, and `lttextcomp.dtx` | Kernel wrappers, aliases, and additional Unicode text symbols                          |
| `unicode-math-table.tex`  | [`unicode-math` symbol table](https://github.com/latex3/unicode-math/blob/master/unicode-math-table.tex)                                 | Unicode identities for math commands                                                   |
| `unicode-math-luatex.sty` | [`unicode-math` symbol aliases](https://github.com/latex3/unicode-math/blob/master/um-code-epilogue.dtx)                                 | Simple command aliases used to resolve math identities                                 |

`unicode-math` is used as a mapping reference during generation; it is **not**
loaded to make the exported commands available. Its additional commands are
filtered out by the base command inventory. The generator supplies a small set
of explicit semantic aliases for composed commands absent from its symbol table.
It fails rather than silently dropping an unrecognized standalone math command.

The exact input SHA-256 hashes for this snapshot are:

```text
e5facb872e45c72f3a4d01a5aedc0a399ca5699b2335b2e4ed47f55c513f6af6  fontmath.ltx
e79ede409feff6b4b2ed981aacbadee32f72887ecfbb2153f613e145ee830c52  tuenc.def
19d3b75884681539e1ef7a427af472bfe80d9ff214b84b9ca45e790d3e89c5c4  latex.ltx
3976ff8f39c84b61055b1cb6851a1b2cfdefa918a2a642c954e6ceafdca7277e  unicode-math-table.tex
b901badb8469dc6b004d51e5fd5706f761d000972ade219b57ac01731504a94f  unicode-math-luatex.sty
```

Regenerate from an installation containing the LaTeX base and `unicode-math`:

```bash
uv run python src/export_latex.py
```

The exporter prints the input hashes and sorts rows by numeric code-point
sequence, then by LaTeX expression and mode to break ties. It writes columns
in the order `code_points`, `text`, `mode`, `latex_code`.
To compare another installation
without replacing the checked-in snapshot:

```bash
uv run python src/export_latex.py --output /tmp/latex2e.tsv
```

Structural and mapping checks run without TeX installed:

```bash
uv run python -m unittest tests.test_export_latex
tombi lint --offline latex/schema.toml
```

The generated snapshot was also checked by typesetting every expression in each
declared mode with base LuaLaTeX, using `article` and no additional packages.
All expressions compiled. The default Latin Modern text font lacked five target
glyphs: U+25EF, U+02F5, U+20B2, U+2E18, and U+02F7. Those mappings remain in the
table because they are explicitly declared by the kernel; font coverage is a
separate constraint. This smoke check verifies command availability, not the
visual equivalence of every rendered glyph.

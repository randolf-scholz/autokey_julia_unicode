# Unicode Icons

The tab-separated value (TSV) files in this directory define Unicode replacement
text and completion abbreviations for AutoKey. See the
[project installation instructions](../../README.md#installation) to install the
bundled tables, or [Contributing](../../CONTRIBUTING.md) for development setup and tests.

## Collections

| Path     | Contents                                                                     |
|----------|------------------------------------------------------------------------------|
| `julia/` | Julia's LaTeX and emoji completions, including the bundled `icons-julia.tsv` |
| `custom` | Additional Unicode characters and custom abbreviations                       |

The installer discovers each immediate subdirectory as one collection. It
combines that directory's `*.tsv` files into a single output folder and checks
duplicates across those tables. Julia and custom collections are independent.

## Icon TSV format

The shared [icon TSV schema](../schemas/icons.toml) defines the columns and
serialization rules for completion tables and UCD character tables.

| Column            | Meaning                                                                       |
|-------------------|-------------------------------------------------------------------------------|
| `code_points`     | Ordered Unicode scalar values, separated by comma-space                       |
| `chars`           | Exact replacement text; an empty cell means reconstruct it from `code_points` |
| `tab_completions` | Completion aliases separated by comma-space, without the triggering space     |
| `unicode_name`    | Current Unicode names in code-point order, separated by comma-space           |

The `chars` column stores the actual replacement text, including combining
marks without display padding such as non-breaking spaces (NBSPs). It must
equal the decoded `code_points` exactly, including all variation selectors.
Leave `chars` empty for replacements containing a tab, CR, or LF so that each TSV
record stays on one line. Quotes and backslashes are literal data; fields are
neither quoted nor escaped.

Names use letters, digits, spaces, and hyphens and must be nonempty. Characters
without a formal name use their first alias from `NameAliases.txt`.
A base character followed by a variation selector may use the base
name alone; generated Julia tables include both names.

## Julia Unicode Icons

The bundled `julia/icons-julia.tsv` table contains Julia's
Unicode completion replacements and their abbreviations. The
[Julia Unicode input table](https://docs.julialang.org/en/v1/manual/unicode-input/)
documents these completions.

Installing the bundled tables requires Python ≥3.12.3 and AutoKey ≥0.96.0 on X11.
Julia ≥1.11 is optional and is only required to regenerate the tables.

Generate a table for the installed Julia version from the repository root:

```sh
just import-julia
```

Without just, run `julia --startup-file=no src/import_julia.jl`.
This writes `data/icons/julia/icons-julia-<julia-version>.local.tsv`, using Julia's
LaTeX and emoji completions and the current names in `third_party/ucd/UnicodeData.txt`.
Missing names fall back to the first alias in `third_party/ucd/NameAliases.txt`.
An optional output path can be passed as the first argument. The UCD input and
default output are located relative to the script, so the script can also run
from other directories.

The default `.local.tsv` output is ignored by Git. Pass an explicit output path
to update the bundled table: `just import-julia data/icons/julia/icons-julia.tsv`.

Run the import checks with `just test test_import_julia.jl`.

## Custom Unicode Icons

The files in `custom` define custom abbreviations that differ from
Julia's and additional characters absent from Julia's completion tables.

The `dingbats` and `emoticons` files also include variants consisting of the
character itself plus variation selector 16 (VS16, `U+FE0F`) to request emoji
presentation. This lets glyphs such as `✅`, `❌`, `⚠`, or `♻` display as
`✅️`, `❌️`, `⚠️`, or `♻️`, respectively, in applications that support emoji
presentation. Include the variation selector in both `chars` and `code_points`.

## Unicode Character Database tables

`data/ucd/blocks/`, `data/ucd/unicode.tsv`, and `data/ucd/blocks.tsv` are generated
from the locally fetched Unicode Character Database. The block index has its own
columns: `block_start`, `block_end`, and `block_name`.
See the [UCD notes](../../third_party/README.md#unicode-character-database)
for sources, filtering rules, and regeneration instructions.

## Validation

Run commands from the repository root and quote globs so the validator expands
them:

```sh
just validate 'data/icons/julia/*.tsv'
just validate 'data/icons/custom/*.tsv'
```

These checks validate the schema and the relationship between `chars` and
`code_points`. Add `--check-icons` to also check names against `data/ucd/unicode.tsv`.

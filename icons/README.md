# Unicode Icons

The tab-separated value (TSV) files in this directory define Unicode replacement
text and completion abbreviations for AutoKey. See the
[project installation instructions](../README.md#installation) to install the
bundled tables, or [Contributing](../CONTRIBUTING.md) for development setup and tests.

## Collections

| Path | Contents |
| ------ | ---------- |
| `julia_unicode/` | Versioned tables of Julia's LaTeX and emoji completions |
| `custom_unicode/` | Additional Unicode characters and custom abbreviations |
| `ucd/` | Generated tables for individual Unicode Character Database blocks |
| `unicode.tsv` | All retained UCD block rows in code point order |
| `blocks.tsv` | Unicode block names and inclusive hexadecimal ranges |

## Icon TSV format

The [icon TSV schema](schema.toml) defines the columns and serialization rules.
`blocks.tsv` is a separate block index with the columns `block_start`, `block_end`,
and `block_name`.

| Column | Meaning |
| -------- | --------- |
| `code_points` | Ordered Unicode scalar values, separated by comma-space |
| `chars` | Exact replacement text; an empty cell means reconstruct it from `code_points` |
| `tab_completions` | Completion aliases separated by comma-space, without the triggering space |
| `unicode_name` | Unicode character name or sequence description |

The `chars` column stores the actual replacement text, including combining
marks without display padding such as non-breaking spaces (NBSPs). It must
equal the decoded `code_points` exactly, including all variation selectors.
Leave `chars` empty for replacements containing a tab, CR, or LF so that each TSV
record stays on one line. Quotes and backslashes are literal data; fields are
neither quoted nor escaped.

## Julia Unicode Icons

The versioned `julia_unicode/icons-<julia-version>.tsv` files contain Julia's
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
This writes `icons/julia_unicode/icons-<julia-version>.local.tsv`, using Julia's
LaTeX and emoji completions and the names in `third_party/ucd/UnicodeData.txt`.
An optional output path can be passed as the first argument. The UCD input and
default output are located relative to the script, so the script can also run
from other directories.

The default `.local.tsv` output is ignored by Git. Pass an explicit output path
to update a bundled table.

Run the import checks with `just test test_import_julia.jl`.

## Custom Unicode Icons

The files in `custom_unicode/` define custom abbreviations that differ from
Julia's and additional characters absent from Julia's completion tables.

The `dingbats` and `emoticons` files also include variants consisting of the
character itself plus variation selector 16 (VS16, `U+FE0F`) to request emoji
presentation. This lets glyphs such as `✅`, `❌`, `⚠`, or `♻` display as
`✅️`, `❌️`, `⚠️`, or `♻️`, respectively, in applications that support emoji
presentation. Include the variation selector in both `chars` and `code_points`.

## Unicode Character Database tables

`ucd/`, `unicode.tsv`, and `blocks.tsv` are generated from the locally fetched
Unicode Character Database. See the [UCD notes](../third_party/README.md#unicode-character-database)
for sources, filtering rules, and regeneration instructions.

## Validation

Run commands from the repository root and quote globs so the validator expands
them:

```sh
just validate 'icons/julia_unicode/icons-*.tsv'
just validate 'icons/custom_unicode/*.tsv'
```

These checks validate the schema and the relationship between `chars` and
`code_points`. Add `--check-icons` to also check names against `icons/unicode.tsv`.

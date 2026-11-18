# Bundled data

| Directory | Contents |
| --------- | -------- |
| `autokey/` | AutoKey phrase and script sources, plus metadata templates |
| [icons/](icons/README.md) | Julia completions and custom AutoKey abbreviations |
| `ucd/` | Generated Unicode character and block reference tables |
| [latex/](latex/README.md) | LaTeX expressions mapped to Unicode sequences |
| `schemas/` | Shared table schemas and their JSON schema definition |

The installer uses `icons/` as its default collection root. Each immediate
subdirectory is one collection: `icons/julia/` contains Julia's tables, and
`icons/custom_unicode/` contains custom abbreviations. All immediate `*.tsv`
files in a collection share an output directory and duplicate checks.

AutoKey asset sources and templates live in `autokey/`. Scripts delivered to
AutoKey are kept there with their TOML metadata. See the
[asset source documentation](../docs/installation.md#asset-sources) for their formats.

The UCD importer writes per-block tables to `ucd/blocks/`, a combined character
table to `ucd/unicode.tsv`, and a block index to `ucd/blocks.tsv`. Original upstream
files remain in [third_party/ucd/](../third_party/README.md#unicode-character-database).

[schemas/icons.toml](schemas/icons.toml) defines the format shared by completion
tables and UCD character tables. [schemas/latex.toml](schemas/latex.toml) defines
the LaTeX mapping format. Both reuse
[schema-definition.json](schemas/schema-definition.json) to validate the schema
files themselves.

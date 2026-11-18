# Refreshing source data

The bundled tables can be installed without refreshing them. To update them,
run these recipes from the repository root:

| Command | Reads | Writes |
| ------------------------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------- |
| `just fetch-ucd --version 18` | A release from unicode.org | Upstream files in `third_party/ucd/` |
| `just import-ucd` | Local files in `third_party/ucd/` | Block tables in `icons/ucd/`, plus `icons/blocks.tsv` and `icons/unicode.tsv` |
| `just import-julia` | The installed Julia's LaTeX and emoji completions, plus local UCD names | `icons/julia_unicode/icons-<julia-version>.local.tsv` |
| `just import-latex` | An installed TeX distribution with the LaTeX base and `unicode-math` sources | `latex/latex2e.tsv` |

`fetch-ucd` downloads upstream files; the `import-*` recipes convert source data
into this project's tables. Fetch the UCD before importing it or refreshing the
Julia tables when updating Unicode data. `fetch-ucd` also accepts `--version latest`.

Each recipe forwards arguments to its matching script in `src/`, for example
`just import-latex --output /tmp/latex2e.tsv`. The Python recipes use the same
interpreter selection as `just install`. See the [UCD notes](../third_party/README.md),
[Julia table notes](../icons/README.md#julia-unicode-icons), and [LaTeX mapping notes](../latex/README.md)
for details.

Run all tests with `just test`, or select files with a quoted filename glob such
as `just test 'test_import_*'`. Validate the icon tables with
`just validate 'icons/julia_unicode/icons-*.tsv'`.

See [Contributing](../CONTRIBUTING.md) for development environment setup and the full test workflow.

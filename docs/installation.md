# Installation and source data

This guide describes installer options, asset generation, and source data updates.
For the basic installation steps and requirements, see the [README](../README.md#installation).
Run all commands below from the repository root.

## Running the installer

```bash
./src/install_autokey.py
```

If [just](https://github.com/casey/just) is installed, use `just install` as an
alternative. It uses `.venv/bin/python` when available, otherwise `python3`;
set `PYTHON` to override the interpreter used by the Python recipes.
The executable script uses `python3` from `PATH`.

Pass options to either command, for example:

```bash
./src/install_autokey.py --help
just install --help
```

Restart AutoKey after installation to load the installed collections.

## AutoKey version check

The installer checks the AutoKey version and stops if it detects a version below 0.96.0. If the
version cannot be determined, it warns and continues.

## Build and installation behavior

All AutoKey assets are generated under `build/autokey/` in the project root before installation
begins. The entire build directory is cleared at the start of each run; reserve it for disposable
generated files. Keep source files and installed collections outside this directory. Child symlinks
are removed without following them. Each builder creates a fresh collection directory and fails if
its name is already in use. Icon collections use `build/autokey/<source-folder>/`.

After a successful build, all generated collections are moved into the AutoKey target directory.
Existing collections with matching names are replaced after one overwrite confirmation; other
collections are preserved. If installation fails, the previous collections and generated build are
restored. Successful installation leaves the build directory empty.

## Asset sources

### LaTeX snippets

LaTeX snippets are stored in `src/assets/latex_snippets/*.toml`, with `abbreviation.abbreviations`
and a literal multiline `payload`. The installer removes the payload and recursively merges the
remaining overrides with `src/assets/templates/phrase.json`, defaulting the description to the
filename stem and applying the selected send mode. The template leaves `description`, `sendMode`,
and `abbreviation.abbreviations` null until generation supplies them. The resulting `.txt` and
`.json` files are built in `build/autokey/latex_snippets/`.

### Special characters

Special characters use the same TOML format in `src/assets/special_chars/`. Their generated files
are built in `build/autokey/special_chars/` with source filenames such as `tabulator.txt` and
`newline.txt`. Both characters are built and installed together with the other collections, using
the same collection overwrite confirmation.

### Custom scripts

Custom scripts keep their Python code in `src/assets/custom_scripts/*.py`. Each corresponding
`.toml` file contains only metadata overrides for `src/assets/templates/script.json`. Nested
dictionaries are merged recursively; lists and scalar values replace template defaults. The template
leaves `description` and `abbreviation.abbreviations` null, so each script must supply them. The
installer builds the Python and merged JSON files in `build/autokey/custom_scripts/`.

## Build without installing

To build all AutoKey assets without changing an AutoKey installation, run:

```bash
./src/install_autokey.py --build-only --sendmode 2
```

`--dry-run` is an alias for `--build-only`: both write the build files and skip installation of icons and bundled
assets. AutoKey is not required for either option.

## Refreshing source data

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

## Validation and tests

Run all tests with `just test`, or select files with a quoted filename glob such
as `just test 'test_import_*'`. Validate the icon tables with
`just validate 'icons/julia_unicode/icons-*.tsv'`.

See [Contributing](../CONTRIBUTING.md) for development environment setup and the full test workflow.

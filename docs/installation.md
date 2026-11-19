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

### Installation directory

By default, collections are installed under `~/.config/autokey/data/julia_unicode/`,
identified by `DEFAULT_TARGET_DIR`. The selected target is owned entirely by this
extension, including when set explicitly: reinstalling replaces all its contents.
Keep personal phrases and scripts elsewhere in the AutoKey data directory.

The module constant `AUTOKEY_DIR` identifies `~/.config/autokey/data/`; this
directory must already exist when using the default destination. If it is missing,
the installer errors before prompting or building. Start AutoKey once to initialize
its data directory, or provide a destination explicitly:

```bash
./src/install_autokey.py --autokey-directory /path/to/autokey/collection
```

An explicit destination can be created during installation. `--target-directory`
appends a subdirectory to the selected destination, or overrides it with an
absolute path. Build-only runs do not require the default AutoKey data directory.
The target cannot be the AutoKey data root or one of its parents, and it must
neither contain nor be inside the build directory.

## AutoKey version check

The installer checks the AutoKey version and stops if it detects a version below 0.96.0. If the
version cannot be determined, it warns and continues.

## Build and installation behavior

All AutoKey assets are generated under `build/autokey/` in the project root before installation
begins. Previous generated assets are cleared at the start of each build; reserve this directory
for disposable generated files and the installation log. Keep source files and installed collections outside this directory. Child symlinks
are removed without following them. Each builder creates a fresh collection directory and fails if
its name is already in use. Icon collections use `build/autokey/<source-folder>/`.

By default, `data/icons/julia/` and `data/icons/custom/` supply the icon collections.
Pass other collection roots as positional arguments; each immediate subdirectory
becomes a collection combining its `*.tsv` files, with duplicate checks per collection.

`build_assets()` builds every collection, including all special characters. It does
not prompt or modify an AutoKey installation; the send mode and duplicate policy
are supplied by the caller.

### Installing built assets

`install_build()` installs from a copy of the completed build without modifying
the generated files:

1. If the target exists, ask once whether to replace the entire directory and all
   its contents. Declining leaves the installation and complete build unchanged.
2. Ask separately whether to install each special character, including `newline`
   and `tabulator`. Each defaults to skipping; choose tabulator and skip newline
   to install only the tab abbreviation.
3. Copy the build to a temporary staging directory beside the target and omit
   unselected special-character payloads and metadata from that copy.
4. Move the existing target aside, then put the staged installation in its place.
   If replacement fails, restore the previous target. On success, remove the old
   target and retain the complete build alongside `install.log`.

All prompts happen before modifying the target. The complete build is retained
after success, cancellation, or installation failure, including optional characters
that were declined. It contains independent copies of all installed files and
is cleared when the next build starts. A target symlink is replaced without
deleting the directory it points to.
If restoring the previous target also fails, its backup is retained and its path
is logged for recovery.

### Logging

Regular runs show file and collection summaries on the console. Individual
skipped characters, duplicates, and generated files are logged at DEBUG level;
use `--verbose` to show those details on the console too.

Each TSV produces one summary starting with its filename, for example:

```text
INFO: data/icons/custom/arrows.tsv: 34 phrases, 0 skipped, 0 duplicate characters skipped.
```

On terminals, paths are blue and created counts are green. Nonzero skipped
counts are yellow and duplicate counts are red; zero skipped/duplicate counts
are gray. Redirected output and the log remain plain text. Set `NO_COLOR` to
disable colors in the terminal.

Every build/install run writes the full DEBUG log to `build/autokey/install.log`,
including prompt choices and failure tracebacks. The log is replaced on the next
run and remains available after successful installation, cancellation, or failure.
It is not copied into AutoKey's installation directory.

## Asset sources

### LaTeX snippets

LaTeX snippets are stored in `data/autokey/latex_snippets/*.toml`, with `abbreviation.abbreviations`
and a literal multiline `payload`. The installer removes the payload and recursively merges the
remaining overrides with `data/autokey/templates/phrase.json`, defaulting the description to the
filename stem and applying the selected send mode. The template leaves `description`, `sendMode`,
and `abbreviation.abbreviations` null until generation supplies them. The resulting `.txt` and
`.json` files are built in `build/autokey/latex_snippets/`.

### Special characters

Special characters use the same TOML format in `data/autokey/special_chars/`. Their generated files
are built in `build/autokey/special_chars/` with source filenames such as `tabulator.txt` and
`newline.txt`. Both are always built. Installation asks about each individually
and includes only the selected payload/metadata pairs.

### Custom scripts

Custom scripts keep their Python code in `data/autokey/custom_scripts/*.py`. Each corresponding
`.toml` file contains only metadata overrides for `data/autokey/templates/script.json`. Nested
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
Build-only runs do not prompt; when `--sendmode` is omitted, they use mode 0
(`<ctrl>+v`). Ordinary installation prompts for a send mode when it is omitted.

## Refreshing source data

The bundled tables can be installed without refreshing them. To update them,
run these recipes from the repository root:

| Command | Reads | Writes |
| --- | --- | --- |
| `just fetch-ucd --version 18` | A release from unicode.org | Upstream files in `third_party/ucd/` |
| `just import-ucd` | Local files in `third_party/ucd/` | Block tables in `data/ucd/blocks/`, plus `data/ucd/blocks.tsv` and `data/ucd/unicode.tsv` |
| `just import-julia` | The installed Julia's LaTeX and emoji completions, plus local UCD names | `data/icons/julia/icons-julia-<julia-version>.local.tsv` |
| `just import-latex` | An installed TeX distribution with the LaTeX base and `unicode-math` sources | `data/latex/latex2e.tsv` |

`fetch-ucd` downloads upstream files; the `import-*` recipes convert source data
into this project's tables. Fetch the UCD before importing it or refreshing the
Julia tables when updating Unicode data. `fetch-ucd` also accepts `--version latest`.

Each recipe forwards arguments to its matching script in `src/`, for example
`just import-latex --output /tmp/latex2e.tsv`. The Python recipes use the same
interpreter selection as `just install`. See the [UCD notes](../third_party/README.md),
[Julia table notes](../data/icons/README.md#julia-unicode-icons), and [LaTeX mapping notes](../data/latex/README.md)
for details.

## Validation and tests

Run all tests with `just test`, or select files with a quoted filename glob such
as `just test 'test_import_*'`. Validate the icon tables with
`just validate data/icons` to check all nested TSVs (default schema: `data/schemas/icons.toml`).

See [Contributing](../CONTRIBUTING.md) for development environment setup and the full test workflow.

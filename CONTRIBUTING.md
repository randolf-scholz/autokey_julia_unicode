# Contributing

Run the commands below from the repository root. For installation and everyday
usage, see the [README](README.md).

## Development environment

Install [uv](https://docs.astral.sh/uv/) and
[just](https://github.com/casey/just), then create a Python virtual environment
and install the locked development dependencies:

```sh
uv venv --python 3.12
uv sync --locked --dev
source .venv/bin/activate
```

The project requires Python ≥3.12.3. Development dependencies are declared in
`pyproject.toml`; `uv.lock` records the resolved versions. `uv sync` installs
prek, Ruff, Pyrefly, Tombi, and the AutoKey Python package into `.venv`.

The Python recipes in `justfile` use `.venv/bin/python` when available. Set
`PYTHON` to override the interpreter. `uv run` also uses the project environment
without requiring activation.

Julia ≥1.11 is required for Julia tests and refreshing Julia's completion tables.
Importing LaTeX mappings requires an installed TeX distribution with `kpsewhich`,
the LaTeX base sources, and `unicode-math`. The Python tests do not require TeX
or a running AutoKey instance.

## Git hooks

[prek](https://prek.j178.dev/) is installed with the development dependencies.
With the virtual environment active, register the Git hooks:

```sh
prek install
```

The configuration in [prek.toml](prek.toml) requires prek ≥0.5.10. Keep the
virtual environment active when committing: the local Pyrefly hook uses
`pyrefly` from `PATH`. Other hooks use environments managed by prek; the first
run may download their tools and runtimes.

Run all configured hooks before submitting changes:

```sh
prek run --all-files
```

Hooks check whitespace, file formats, Python imports and formatting, Python
lint and types, TOML, Markdown, shell scripts, and JSON formatting. Some hooks
modify files; review those changes and rerun the checks.

## Linting and formatting

Run individual Python checks with:

```sh
uv run ruff check src tests
uv run ruff check --select I src tests
uv run ruff format --check src tests
uv run pyrefly check src tests
```

To apply Python import sorting and formatting:

```sh
uv run ruff check --select I --fix src tests
uv run ruff format src tests
```

Check the project configuration and table schemas with:

```sh
uv run tombi lint --offline pyproject.toml icons/schema.toml latex/schema.toml
```

Use `prek run --all-files` for the complete set of checks, including Markdown.

## Testing

Run all Python and Julia tests with:

```sh
just test
```

Select test files with a quoted filename glob, or run an individual file:

```sh
just test 'test_import_*'
just test test_fetch_ucd.py
just test test_import_julia.jl
```

Without just, or when Julia is unavailable, run the Python suite separately:

```sh
uv run python -m unittest discover -s tests -p 'test_*.py'
```

Run Julia checks directly with:

```sh
julia --startup-file=no tests/test_import_julia.jl
```

To inspect generated AutoKey assets without changing an installation:

```sh
just install --build-only
```

This writes to `build/autokey/`, clearing its previous contents. AutoKey is not
required for a build-only run.

## Data and documentation

See the [icon documentation](icons/README.md) for collections, the TSV format,
and validation commands. The [main README](README.md#refreshing-source-data)
lists data refresh recipes; [third-party notes](third_party/README.md) document
upstream sources, and [LaTeX mapping notes](latex/README.md) describe mapping
coverage and provenance.

Keep documentation in the root or top-level directory READMEs instead of adding
READMEs inside collection directories. When changing behavior, update the
relevant documentation and [changelog](CHANGELOG.md).

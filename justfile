[doc("Show available recipes.")]
default:
    @just --list

[doc("Install Unicode character abbreviations for AutoKey.")]
[positional-arguments]
install *args:
    #!/usr/bin/env bash
    set -euo pipefail
    python="${PYTHON:-python3}"
    if [[ -z "${PYTHON:-}" && -x .venv/bin/python ]]; then
        python=.venv/bin/python
    fi
    exec "$python" src/install_autokey.py "$@"

[doc("Import the running Julia version's Unicode completions.")]
[positional-arguments]
import-julia *args:
    julia --startup-file=no src/import_julia.jl "$@"

[doc("Import the locally fetched UCD into per-block Unicode TSV files.")]
[positional-arguments]
import-ucd *args:
    #!/usr/bin/env bash
    set -euo pipefail
    python="${PYTHON:-python3}"
    if [[ -z "${PYTHON:-}" && -x .venv/bin/python ]]; then
        python=.venv/bin/python
    fi
    exec "$python" src/import_ucd.py "$@"

[doc("Download and validate a Unicode Character Database release.")]
[positional-arguments]
fetch-ucd *args:
    #!/usr/bin/env bash
    set -euo pipefail
    python="${PYTHON:-python3}"
    if [[ -z "${PYTHON:-}" && -x .venv/bin/python ]]; then
        python=.venv/bin/python
    fi
    exec "$python" src/fetch_ucd.py "$@"

[doc("Import base LaTeX symbol mappings from an installed TeX distribution.")]
[positional-arguments]
import-latex *args:
    #!/usr/bin/env bash
    set -euo pipefail
    python="${PYTHON:-python3}"
    if [[ -z "${PYTHON:-}" && -x .venv/bin/python ]]; then
        python=.venv/bin/python
    fi
    exec "$python" src/import_latex.py "$@"

[doc("Validate TSV files or path globs (quote globs at the CLI).")]
[positional-arguments]
validate +args:
    #!/usr/bin/env bash
    set -euo pipefail
    python="${PYTHON:-python3}"
    if [[ -z "${PYTHON:-}" && -x .venv/bin/python ]]; then
        python=.venv/bin/python
    fi
    exec "$python" src/validate_tsv.py "$@"

[doc("Run Python and Julia test files matching a filename glob (quote globs at the CLI).")]
test name='*':
    #!/usr/bin/env bash
    set -euo pipefail
    pattern={{quote(name)}}
    python="${PYTHON:-python3}"
    if [[ -z "${PYTHON:-}" && -x .venv/bin/python ]]; then
        python=.venv/bin/python
    fi
    python_tests=()
    julia_tests=()
    for file in tests/test_*.py tests/test_*.jl; do
        [[ -f "$file" ]] || continue
        filename="${file##*/}"
        [[ "$filename" == $pattern ]] || continue
        case "$file" in
            *.py) python_tests+=("$file") ;;
            *.jl) julia_tests+=("$file") ;;
        esac
    done
    if (( ${#python_tests[@]} + ${#julia_tests[@]} == 0 )); then
        echo "No test files match: $pattern" >&2
        exit 1
    fi
    if (( ${#python_tests[@]} )); then
        if [[ "$pattern" == '*' ]]; then
            "$python" -m pytest tests
        else
            "$python" -m pytest "${python_tests[@]}"
        fi
    fi
    for file in "${julia_tests[@]}"; do
        echo "Running $file"
        julia --startup-file=no "$file"
    done

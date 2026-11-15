# Install Unicode character abbreviations for AutoKey.
[positional-arguments]
install *args:
    #!/usr/bin/env bash
    set -euo pipefail
    python="${PYTHON:-python3}"
    if [[ -z "${PYTHON:-}" && -x .venv/bin/python ]]; then
        python=.venv/bin/python
    fi
    exec "$python" src/install_autokey.py "$@"

# Run Python and Julia test files matching a filename glob (quote globs at the CLI).
test name='*':
    #!/usr/bin/env bash
    set -euo pipefail
    pattern={{quote(name)}}
    python="${PYTHON:-python3}"
    if [[ -z "${PYTHON:-}" && -x .venv/bin/python ]]; then
        python=.venv/bin/python
    fi
    matched=false
    for file in tests/test_*.py tests/test_*.jl; do
        [[ -f "$file" ]] || continue
        filename="${file##*/}"
        [[ "$filename" == $pattern ]] || continue
        matched=true
        echo "Running $file"
        case "$file" in
            *.py) "$python" -m unittest discover -s tests -p "$filename" ;;
            *.jl) julia --startup-file=no "$file" ;;
        esac
    done
    if [[ "$matched" == false ]]; then
        echo "No test files match: $pattern" >&2
        exit 1
    fi

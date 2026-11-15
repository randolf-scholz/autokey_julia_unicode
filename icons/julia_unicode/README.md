# Julia Unicode Icons

`icons.tsv` contains tabular separated value (TSV) files that define the Unicode
characters used in Julia, along with their corresponding abbreviations.

This table can be found in the Julia documentation <https://docs.julialang.org/en/v1/manual/unicode-input/>

Generate a table for the installed Julia version (Julia 1.11 or newer) with:

```sh
julia src/export_julia.jl
```

This writes `icons/julia_unicode/icons-<julia-version>.tsv`, using Julia's
LaTeX and emoji completions and the names in `third_party/ucd/UnicodeData.txt`.
An optional output path can be passed as the first argument. The imported UCD and
default output are located relative to the script, so the script can also run
from other directories.

Run the export checks with `julia tests/test_export_icons.jl`.

# Third Party Libraries

## $\LaTeX$ package 'comprehensive'

The [comprehensive](https://ctan.org/pkg/comprehensive) package is a collection of symbols and macros for $\LaTeX$. We can use it as a reference for $\LaTeX$ macros that can be used to substitute unicode characters when using `pdflatex`.

## Unicode Character Database

The [Unicode Character Database](https://www.unicode.org/ucd/) is a collection of files that define the properties of all Unicode characters. We can use it to generate a list of all unicode characters that are supported by our system.

The bundled data is Unicode **18.0.0**. Refresh it from the repository root with:

```sh
python src/import_ucd.py --version 18
```

Use `--version 17` for Unicode 17.0.0 or `--version latest` for the latest release.
Explicit versions use the requested release's URLs.
Versions can be written as `18`, `18.0`, or `18.0.0`.

The importer downloads these files directly from Unicode, validates them, and
overwrites their local copies only after all downloads and checks succeed:

| Local file | Upstream source for Unicode 18.0.0 |
| --- | --- |
| `ucd/LICENSE` | <https://www.unicode.org/license.txt> |
| `ucd/Blocks.txt` | <https://www.unicode.org/Public/18.0.0/ucd/Blocks.txt> |
| `ucd/ReadMe.txt` | <https://www.unicode.org/Public/18.0.0/ucd/ReadMe.txt> |
| `ucd/UnicodeData.txt` | <https://www.unicode.org/Public/18.0.0/ucd/UnicodeData.txt> |

The license URL provides the current Unicode license, independently of the data
release. The three UCD files retain their upstream contents and filenames.

Generate the block tables in `icons/ucd` from the imported data with:

```sh
python src/export_ucd.py
```

This standard-library replacement for `experimental/extract_blocks.ipynb` writes
one TSV per block using the notebook's filenames and seven columns. It exports
explicit `UnicodeData.txt` records without expanding First/Last range markers,
and omits surrogate symbols so every output file is valid UTF-8. Obsolete block
TSVs are removed when regenerating the directory. Use `--source-dir` and
`--output-dir` to select other input and output directories.

## Latex packages

- `stix`: LPPL
- `stix2`: LPPL
- `fdsymbol`: LPPL
- `MnSymbol`: public domain
- `newunicodechar`: LPPL
- `subdepth`: LPPL
- `amssymb`: no modifications allowed
- `amsfonts`: no modifications allowed

The math symbols provided by core LaTeX are not included in the list of packages, as they are part of the core LaTeX distribution, whose license requires shipping a full copy of the source code.

- `fontmath.ltx`: not included.
- `latexsym.sty`: not included.

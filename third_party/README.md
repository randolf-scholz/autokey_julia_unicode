# Third Party Libraries

## $\LaTeX$ package 'comprehensive'

The [comprehensive](https://ctan.org/pkg/comprehensive) package is a collection of symbols and macros for $\LaTeX$. We
can use it as a reference for $\LaTeX$ macros that can be used to substitute unicode characters when using `pdflatex`.

## Unicode Character Database

The [Unicode Character Database](https://www.unicode.org/ucd/) is a collection of files that define the properties of
all Unicode characters. We can use it to generate a list of all unicode characters that are supported by our system.

The bundled data is Unicode **18.0.0**. Refresh it from the repository root with:

```sh
python src/fetch_ucd.py --version 18
```

Use `--version 17` for Unicode 17.0.0 or `--version latest` for the latest release.
Explicit versions use the requested release's URLs.
Versions can be written as `18`, `18.0`, or `18.0.0`.

The fetcher downloads these files directly from Unicode, validates them, and
overwrites their local copies only after all downloads and checks succeed:

| Local file            | Upstream source for Unicode 18.0.0                          |
|-----------------------|-------------------------------------------------------------|
| `ucd/LICENSE`         | <https://www.unicode.org/license.txt>                       |
| `ucd/Blocks.txt`      | <https://www.unicode.org/Public/18.0.0/ucd/Blocks.txt>      |
| `ucd/ReadMe.txt`      | <https://www.unicode.org/Public/18.0.0/ucd/ReadMe.txt>      |
| `ucd/UnicodeData.txt` | <https://www.unicode.org/Public/18.0.0/ucd/UnicodeData.txt> |

The license URL provides the current Unicode license, independently of the data
release. The three UCD files retain their upstream contents and filenames.

Generate the block tables in `icons/unicode_blocks` from the imported data with:

```sh
python src/import_ucd.py
```

This standard-library importer writes one TSV per block using the columns and
order in `icons/schema.toml`: `code_points`, `chars`, `tab_completions`,
`unicode_name`, and `base`. Completion aliases and base values are empty.
Unicode names retain their exact uppercase spelling; unnamed characters have
empty names. Compressed First/Last ranges, including their endpoint records,
are skipped to keep the symbol tables compact. Explicit mathematical symbols
remain included. Surrogate symbols are omitted so every output file is valid
UTF-8; blocks with no retained characters contain only the header.

`icons/blocks.tsv` lists each block's inclusive hexadecimal `block_start` and
`block_end` (without `U+`) and its `block_name`. `icons/unicode.tsv` concatenates
all block rows in code point order under a single schema header. Obsolete block
TSVs are removed when regenerating the directory. Use `--source-dir` and
`--output-dir` to select other input and block output directories; the two
summary TSVs are written to the block directory's parent.

## Latex packages

- `stix`: LPPL
- `stix2`: LPPL
- `fdsymbol`: LPPL
- `MnSymbol`: public domain
- `newunicodechar`: LPPL
- `subdepth`: LPPL
- `amssymb`: no modifications allowed
- `amsfonts`: no modifications allowed

The math symbols provided by core LaTeX are not included in the list of packages, as they are part of the core LaTeX
distribution, whose license requires shipping a full copy of the source code.

- `fontmath.ltx`: not included.
- `latexsym.sty`: not included.

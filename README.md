# AutoKey Unicode characters

[Contributing](CONTRIBUTING.md) | [License](LICENSE) | [Changelog](CHANGELOG.md)

[Usage](#usage) | [Requirements](#requirements) | [Installation](#installation) | [Features](#features) | [Known Issues](#known-issues--limitations) | [References](#references)

![demo](demo.gif)

## Usage

This script adds all the Unicode character abbreviations supported
by [Julia](https://docs.julialang.org/en/v1/manual/unicode-input/#Unicode-Input) to AutoKey. However, instead of
`[TAB]`, they are triggered on `[SPACE]`. If you do not want to perform the replacement, simply hit `[BACKSPACE]`
afterwards.

## Requirements

- Python ≥3.12.3.
- [AutoKey](https://github.com/autokey/autokey) ≥0.96.0, running on X11. Wayland is unsupported.
- Julia ≥1.11 (optional), only needed to regenerate the Julia Unicode tables. Installing the bundled tables does not
  require Julia.

## Installation

1. Install [AutoKey](https://github.com/autokey/autokey). Only works on X11, no Wayland support.
2. From the repository root, run:

   ```bash
   ./src/install_autokey.py
   ```

   If you have [just](https://github.com/casey/just) installed, you can alternatively run:

   ```bash
   just install
   ```

   `just install` uses `.venv/bin/python` when available, otherwise `python3`. Set `PYTHON` to override the interpreter.
   Pass installer options to either command, for example `./src/install_autokey.py --help`.

3. Restart AutoKey

The installer checks the AutoKey version and stops if it detects a version below 0.96.0. If the version cannot be
determined, it warns and continues.

All AutoKey assets are generated under `build/autokey/` in the project root before installation begins. The entire build
directory is cleared at the start of each run; reserve it for disposable generated files. Keep source files and
installed
collections outside this directory. Child symlinks are removed without following them. Each builder creates a fresh
collection directory and fails if its name is already in use. Icon collections use `build/autokey/<source-folder>/`.

After a successful build, all generated collections are moved into the AutoKey target directory. Existing collections
with matching names are replaced after one overwrite confirmation; other collections are preserved. If installation
fails, the previous collections and generated build are restored. Successful installation leaves the build directory
empty.

LaTeX snippets are stored in `src/assets/latex_snippets/*.toml`, with `abbreviation.abbreviations` and a literal
multiline
`payload`. The installer removes the payload and recursively merges the remaining overrides with
`src/assets/templates/phrase.json`, defaulting the description to the filename stem and applying the selected send mode.
The template leaves `description`, `sendMode`, and `abbreviation.abbreviations` null until generation supplies them.
The resulting `.txt` and `.json` files are built in `build/autokey/latex_snippets/`.

Special characters use the same TOML format in `src/assets/special_chars/`. Their generated files are built in
`build/autokey/special_chars/` with source filenames such as `tabulator.txt` and `newline.txt`. Both characters are
built
and installed together with the other collections, using the same collection overwrite confirmation.

Custom scripts keep their Python code in `src/assets/custom_scripts/*.py`. Each corresponding `.toml` file contains
only metadata overrides for `src/assets/templates/script.json`. Nested dictionaries are merged recursively; lists and
scalar values replace template defaults. The template leaves `description` and `abbreviation.abbreviations` null, so
each script must supply them. The installer builds the Python and merged JSON files in `build/autokey/custom_scripts/`.

To build all AutoKey assets without changing an AutoKey installation, run:

```bash
./src/install_autokey.py --build-only --sendmode 2
```

`--dry-run` is an alias for `--build-only`: both write the build files and skip installation of icons and bundled
assets. AutoKey is not required for either option.

## Refreshing source data

The bundled tables can be installed without refreshing them. To update them,
run these recipes from the repository root:

| Command                       | Reads                                                                        | Writes                                                                        |
|-------------------------------|------------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| `just fetch-ucd --version 18` | A release from unicode.org                                                   | Upstream files in `third_party/ucd/`                                          |
| `just import-ucd`             | Local files in `third_party/ucd/`                                            | Block tables in `icons/ucd/`, plus `icons/blocks.tsv` and `icons/unicode.tsv` |
| `just import-julia`           | The installed Julia's LaTeX and emoji completions, plus local UCD names      | `icons/julia_unicode/icons-.local.tsv`                                        |
| `just import-latex`           | An installed TeX distribution with the LaTeX base and `unicode-math` sources | `latex/latex2e.tsv`                                                           |

`fetch-ucd` downloads upstream files; the `import-*` recipes convert source data
into this project's tables. Fetch the UCD before importing it or refreshing the
Julia tables when updating Unicode data. `fetch-ucd` also accepts `--version latest`.

Each recipe forwards arguments to its matching script in `src/`, for example
`just import-latex --output /tmp/latex2e.tsv`. The Python recipes use the same
interpreter selection as `just install`. See the [UCD notes](third_party/README.md),
[Julia table notes](icons/README.md#julia-unicode-icons), and [LaTeX mapping notes](latex/README.md)
for details.

Run all tests with `just test`, or select files with a quoted filename glob such
as `just test 'test_import_*'`. Validate the icon tables with
`just validate 'icons/julia_unicode/icons-*.tsv'`.

## Features

For overview see [Supported Alphabets](#supported-alphabets)

### Advantages of Unicode

1. Work even when MathJax / LaTeX is not available (e.g. E-mails, chat clients, etc.)
2. Is character efficient (e.g. when writing comments on <https://math.stackexchange.com>)
3. Increases readability of source code.
4. Copy-paste persistent.

### Compatibility with MathJax & LaTeX

1. MathJax supports Unicode characters: `$\sin(\theta)$` and `$\sin(θ)$` should look exactly the same.
2. [LuaLaTeX](http://www.luatex.org/) has Unicode compatibility, at least in math-mode when using
   the [unicode-math](https://github.com/wspr/unicode-math) package.
3. For PDFLaTeX support, see the separate [latex-unicode](https://github.com/randolf-scholz/latex-unicode) project.

### Supported Alphabets

To create single characters of the given alphabet, simply type `\<modifier><char><space>`.

- For blackboard bold R, `ℝ`, type `\bbR␣`.
- For a circled one, `①`, type `\o1␣`.
- For a bold italic capital gamma, `𝜞`, type `\biGamma␣`.
- For the sub and superscripts, `Xᵢ²`, type `X\_i␣\^2␣`.
- For the Roman numeral `Ⅷ` (this is a single UTF-8 glyph, and not `V`+`I`+`I`+`I`), type `\RM8␣`.

#### Serif Font

| family | `\bf<>` | `\it<>` | `\bi<>` |
|--------|---------|---------|---------|
| Latin  | 𝐚𝐛𝐜𝐀𝐁𝐂  | 𝑎𝑏𝑐𝐴𝐵𝐶  | 𝒂𝒃𝒄𝑨𝑩𝑪  |
| Greek  | 𝛂𝛃𝛄𝚨𝚩𝚪  | 𝛼𝛽𝛾𝛢𝛣𝛤  | 𝜶𝜷𝜸𝜜𝜝𝜞  |
| Digits | 𝟎𝟏𝟐     | —       | —       |

#### Sans Serif Font

| family      | `\sans<>` | `\bsans<>` | `\isans<>` | `\bisans<>` |
|-------------|-----------|------------|------------|-------------|
| Latin upper | 𝖠𝖡𝖢       | 𝗔𝗕𝗖        | 𝘈𝘉𝘊        | 𝘼𝘽𝘾         |
| Latin lower | 𝖺𝖻𝖼       | 𝗮𝗯𝗰        | 𝘢𝘣𝘤        | 𝙖𝙗𝙘         |
| Greek upper | —         | 𝝖𝝗𝝘        | —          | 𝞐𝞑𝞒         |
| Greek lower | —         | 𝝰𝝱𝝲        | —          | 𝞪𝞫𝞬         |
| Digits      | 𝟢𝟣𝟤       | 𝟬𝟭𝟮        | —          | —           |

#### Specialty Font

| family      | `\tt<>` | `\bb<>` | `\frak<>` | `\bfrak<>` | `\scr<>` | `\bscr<>` |
|-------------|---------|---------|-----------|------------|----------|-----------|
| Latin upper | 𝙰𝙱𝙲     | 𝔸𝔹ℂ     | 𝔄𝔅ℭ       | 𝕬𝕭𝕮        | 𝒜ℬ𝒞      | 𝓐𝓑𝓒       |
| Latin lower | 𝚊𝚋𝚌     | 𝕒𝕓𝕔     | 𝔞𝔟𝔠       | 𝖆𝖇𝖈        | 𝒶𝒷𝒸      | 𝓪𝓫𝓬       |
| Digits      | 𝟶𝟷𝟸     | 𝟘𝟙𝟚     | —         | —          | —        | —         |

#### Numerals

| family | `\<>.` | `\rm<>` | `\RM<>` |
|--------|--------|---------|---------|
| 0      | —      | —       | —       |
| 1      | ⒈      | ⅰ       | Ⅰ       |
| 2      | ⒉      | ⅱ       | Ⅱ       |
| 3      | ⒊      | ⅲ       | Ⅲ       |

#### Other Families

| family      | `\^<>` | `\_<>` | `\o<>` | `\(<>)` | `\sc<>` | `\fw<>` |
|-------------|--------|--------|--------|---------|---------|---------|
| Latin upper | ᴵᴶᴷ    | —      | ⒶⒷⒸ    | —       | ᴀʙᴄᴅ    | ＡＢＣ  |
| Latin lower | ⁱʲᵏ    | ᵢⱼₖ    | ⓐⓑⓒ    | ⒜⒝⒞     | —       | ａｂｃ  |
| Greek upper | —      | —      | —      | —       | —       | —       |
| Greek lower | ᵝᵞᵠ    | ᵦᵧᵩ    | —      | —       | —       | —       |
| Digits      | ⁰¹²    | ₀₁₂    | ⓪①②    | ⑴⑵⑶     | —       | ０１２  |

Note: Generally here not all characters are available:

- Small capital letters is missing `\scX`.
- Sub- and superscripts is missing quite a few letters,
  see: <https://en.wikipedia.org/wiki/Unicode_subscripts_and_superscripts>.

## Known Issues & Limitations

- When using the `Markdown All in One` extension for VS Code, make sure to disable the `backspace` hotkey, otherwise
  `AutoKey` will not be able to insert the Unicode characters.
- So far was only tested with Ubuntu 20.04 LTS and `Autokey` 0.95.10
- Seems to behave weird with **Gnome Terminal**, no idea what's going on.
- Can show strange behavior with **VS Code**.
  - Seems fixable by deleting all `[shift]+[insert]` hotkeys combinations. (`File > Preferences > Keyboard Shortcuts`)
  - Our macros here insert symbols with `[shift]+[insert]`
    and [VS Code seems to mess with that](https://github.com/microsoft/vscode/issues/90637)
- Composed characters seem to not always work as intended, not many editors render them correctly.
- Doesn't support multiple sub/super-scripts like Julia does (e.g. in REPL, `a\^(k)+[TAB]`) gives `a⁽ᵏ⁾`. With `AutoKey`
  we need to add the superscripts one at a time.
- Seems like it doesn't work with a German keyboard because `AutoKey` interprets `\` and `[AltGr]+?` (what you type on a
  German keyboard to get backslash) as different things.

### Overleaf Compatibility

If you intend to use <https://overleaf.com>, this platform only supports the first 65536 Unicode characters
([details](https://www.overleaf.com/learn/how-to/What_file_encodings_and_line_endings_should_I_use%3F#Invalid/Unsupported_Characters)).

This is called the "basic plane", which includes for instance the Greek letters 𝛼, 𝛽, 𝛾, but not any characters from the
"supplementary planes", such as
the [Mathematical Alphanumeric Symbols](https://en.wikipedia.org/wiki/Mathematical_Alphanumeric_Symbols) like `𝟙`, `𝔽`,
`𝚪`, `𝓝` or `ℒ`. If you want to use these characters, you need to compile your document locally.

## References

- [Unicode Database](https://www.unicode.org/ucd/)
- [Julia Documentation](https://docs.julialang.org/en/v1/manual/unicode-input/#Unicode-Input)
- [AutoKey Documentation](https://autokey.github.io/documentation.html)
- [Latex Symbols](https://ctan.org/pkg/comprehensive)

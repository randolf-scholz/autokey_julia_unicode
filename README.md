# Autokey Unicode characters

## [CHANGELOG](CHANGELOG.md)

- 2024-02-27: Added italic and bold italic greek variants  to `unicode-symbols.sty`.
- 2024-02-26: Combining subscripts: `$xᵢⱼ$` will render identically to `$x_{ij}$` ($x_{ij}$).
- 2024-01-23: **⚠️ New ⚠️:** Added `unicode-symbols.sty` which provides a useful subset of the unicode characters for usage with `pdflatex`.

![demo](demo.gif)

## Usage

This script adds all the unicode character abbreviations supported by [Julia](https://docs.julialang.org/en/v1/manual/unicode-input/#Unicode-Input) to autokey. However, instead of `[TAB]`, they are triggered on `[SPACE]`. If you do not want perform the replacement, simply hit `[BACKSPACE]` afterwards.

## Installation & Requirements

1. Install [autokey](https://github.com/autokey/autokey). Only works on X11, no Wayland support.
2. Execute `generate_phrases.py` (requires python ≥3.10)
3. Restart autokey

## Features

For overview see [Supported Alphabets](#supported-alphabets)

## Advantages of Unicode

1. Work even when MathJax / LaTeX is not available (e.g. E-mails, chat clients, etc.)
2. Is character efficient (e.g. when writing comments on <https://math.stackexchange.com>)
3. Increases readability of source code.
4. Copy-paste persistent.

## Compatibility with MathJax & LaTeX

1. MathJax supports unicode characters: `$\sin(\theta)$` and `$\sin(θ)$` should look exactly the same.
2. LaTeX has unicode compatibility, at least in math-mode when using the [unicode-math](https://github.com/wspr/unicode-math) package and compiling with [LuaLaTeX](http://www.luatex.org/). For usage with `pdflatex`, try the attached `unicode-symbols.sty` package.

⚠️ **BEWARE** ⚠️ If you intend to use <https://overleaf.com>,
this platform only supports the first 65536 unicode characters
(the "basic plane"). This means that you cannot use any of the characters in the "supplementary planes"
(e.g. the greek letters 𝛼, 𝛽, 𝛾, …). If you want to use these characters, you need to compile your document locally
([details](https://www.overleaf.com/learn/how-to/What_file_encodings_and_line_endings_should_I_use%3F#Invalid/Unsupported_Characters)).

## Known Issues & Limitations

- So far was only tested with Ubuntu 20.04 LTS and Autokey 0.95.10
- Seems to behave weird with **Gnome Terminal**, no idea what's going on.
- Can show strange behaviour with **VSCode**.
  - Seems fixable by deleting all `[shift]+[insert]` hotkeys combinations. (`File > Preferences > Keyboard Shortcuts`)
  - Our macros here insert symbols with `[shift]+[insert]` and [VScode seems to mess with that](https://github.com/microsoft/vscode/issues/90637)
- Composed characters seem to not always work as intended, not many editors render them correctly.
- Doesn't support multiple sub/super-scripts like Julia does (e.g. in REPL, `a\^(k)+[TAB]`) gives a⁽ᵏ⁾. With AutoKey we need to add the superscripts one at a time.
- Seems like it doesnt work with a German keyboard because AutoKey interprets `\` and `[AltGr]+?` (what you type on a German keyboard to get backslash) as different things.

### Supported Alphabets

To create single characters of the given alphabet, simply type `\<modifier><char><space>`.

- For blackboard bold R, `ℝ`, type `\bbR␣`.
- For a circled one, `①`, type `\o1␣`.
- For a bold italic capital gamma, `𝜞`, type `\biGamma␣`.
- For the sub and superscripts, `Xᵢ²`, type `X\_i␣\^2␣`.
- For the roman numeral `Ⅷ` (this is a single UTF-8 glyph, and not `V`+`I`+`I`+`I`), type `\RM8␣`.

#### Serif Font

| family | `bf`   | `it`   | `bi`   |
|--------|--------|--------|--------|
| latin  | 𝐚𝐛𝐜𝐀𝐁𝐂 | 𝑎𝑏𝑐𝐴𝐵𝐶 | 𝒂𝒃𝒄𝑨𝑩𝑪 |
| greek  | 𝛂𝛃𝛄𝚨𝚩𝚪 | 𝛼𝛽𝛾𝛢𝛣𝛤 | 𝜶𝜷𝜸𝜜𝜝𝜞 |
| digits | 𝟎𝟏𝟐    |        |        |

#### Sans Serif Font

| family      | `sans` | `bsans` | `isans` | `bisans` |
|-------------|--------|---------|---------|----------|
| latin upper | 𝖠𝖡𝖢    | 𝗔𝗕𝗖     | 𝘈𝘉𝘊     | 𝘼𝘽𝘾      |
| latin lower | 𝖺𝖻𝖼    | 𝗮𝗯𝗰     | 𝘢𝘣𝘤     | 𝙖𝙗𝙘      |
| greek upper | ⸻      | 𝝖𝝗𝝘     | ⸻       | 𝞐𝞑𝞒      |
| greek lower | ⸻      | 𝝰𝝱𝝲     | ⸻       | 𝞪𝞫𝞬      |
| digits      | 𝟢𝟣𝟤    | 𝟬𝟭𝟮     | ⸻       | ⸻        |

#### Speciality Font

| family      | `tt` | `bb` | `frak` | `bfrak` | `scr` | `bscr` |
|-------------|------|------|--------|---------|-------|--------|
| latin upper | 𝙰𝙱𝙲  | 𝔸𝔹ℂ  | 𝔄𝔅ℭ    | 𝕬𝕭𝕮     | 𝒜ℬ𝒞   | 𝓐𝓑𝓒    |
| latin lower | 𝚊𝚋𝚌  | 𝕒𝕓𝕔  | 𝔞𝔟𝔠    | 𝖆𝖇𝖈     | 𝒶𝒷𝒸   | 𝓪𝓫𝓬    |
| digits      | 𝟶𝟷𝟸  | 𝟘𝟙𝟚  | ⸻      | ⸻       | ⸻     | ⸻      |

#### Other Families

| family      | `^` | `_` | `o` | `rm` | `RM` | `sc` |
|-------------|-----|-----|-----|------|------|------|
| latin upper | ᴵᴶᴷ | ⸻   | ⒶⒷⒸ | ⸻    | ⸻    | ᴀʙᴄᴅ |
| latin lower | ⁱʲᵏ | ᵢⱼₖ | ⓐⓑⓒ | ⸻    | ⸻    | ⸻    |
| greek upper | ⸻   | ⸻   | ⸻   | ⸻    | ⸻    | ⸻    |
| greek lower | ᵝᵞᵠ | ᵦᵧᵩ | ⸻   | ⸻    | ⸻    | ⸻    |
| digits      | ⁰¹² | ₀₁₂ | ⓪①② | ⅰⅱⅲⅳ | ⅠⅡⅢⅣ | ⸻    |

Note: Generally here not all characters are available:

- Small capital letters is missing `\scX`.
- Sub- and superscripts is missing quite a few letters, see: <https://en.wikipedia.org/wiki/Unicode_subscripts_and_superscripts>.

## About Unicode data

The files are available at: <https://www.unicode.org/ucd/>, resp. <https://www.unicode.org/Public/UCD/latest/ucd/>.

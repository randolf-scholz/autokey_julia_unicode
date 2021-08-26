# Autokey Unicode characters

![demo](demo.gif)

## Usage

This script adds all the unicode character abbreviations supported by [Julia](https://docs.julialang.org/en/v1/manual/unicode-input/#Unicode-Input) to autokey. However, instead of `[TAB]`, they are triggered on `[SPACE]`. If you do not want perform the replacement, simply hit `[BACKSPACE]` afterwards.

## Installation

1. Install [autokey](https://github.com/autokey/autokey)
2. Execute `generate_phrases.py` (requires python >3.7)
3. Restart autokey

## Advantages of Unicode

1. Work even when MathJax / LaTeX is not available
2. Is character efficient
3. Increases readability of uncompiled documents
4. Is copy-paste persistent

## Compatibility with MathJax & LaTeX

1. MathJax supports unicode characters: `$\sin(\theta)$` and `$\sin(θ)$` should look exactly the same.
2. LaTeX has unicode compatibility, at least in math-mode when using the [unicode-math](https://github.com/wspr/unicode-math) package and compiling with [LuaLaTeX](http://www.luatex.org/)

## Supported Alphabets

### Serif Font

| family | `bf`   | `it`   | `bi`   |
|--------|--------|--------|--------|
| latin  | 𝐚𝐛𝐜𝐀𝐁𝐂 | 𝑎𝑏𝑐𝐴𝐵𝐶 | 𝒂𝒃𝒄𝑨𝑩𝑪 |
| greek  | 𝛂𝛃𝛄𝚨𝚩𝚪 | 𝛼𝛽𝛾𝛢𝛣𝛤 | 𝜶𝜷𝜸𝜜𝜝𝜞 |
| letter |        |        |        |

### Sans Serif Font

| family | `sans` | `bsans` | `isans` | `bisans` |
|--------|--------|---------|---------|----------|
| latin  | 𝖺𝖻𝖼𝖠𝖡𝖢 | 𝗮𝗯𝗰𝗔𝗕𝗖  | 𝘢𝘣𝘤𝘈𝘉𝘊  | 𝙖𝙗𝙘𝘼𝘽𝘾   |
| greek  |        | 𝝰𝝱𝝲𝝖𝝗𝝘  |         | 𝞪𝞫𝞬𝞐𝞑𝞒   |
| letter | 𝟢𝟣𝟤    | 𝟬𝟭𝟮     |         |          |

### Speciality Font

| family | `tt`   | `bb`   | `frak` | `bfrak` | `scr`  | `bscr` |
|--------|--------|--------|--------|---------|--------|--------|
| latin  | 𝚊𝚋𝚌𝙰𝙱𝙲 | 𝕒𝕓𝕔𝔸𝔹ℂ | 𝔞𝔟𝔠𝔄𝔅ℭ | 𝖆𝖇𝖈𝕬𝕭𝕮  | 𝒶𝒷𝒸𝒜ℬ𝒞 | 𝓪𝓫𝓬𝓐𝓑𝓒 |
| greek  |        |        |        |         |        |        |
| letter | 𝟶𝟷𝟸    | 𝟘𝟙𝟚    |        |         |        |        |

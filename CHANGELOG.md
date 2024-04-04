# CHANGELOG

## 2024-04-04

Added transpose and hermitian transpose: `A𞁀` and `Aᵸ`.

Key combinations: `\transpose`/`\hermitian` or provisional `\tp`/`\htp`

We abuse the two Cyrillic characters:

- `𞁀`: U+1E040 Modifier Letter Cyrillic Small Te
- `ᵸ`: U+0480 U+1D78 Modifier Letter Cyrillic En

In `unicode-symbols.sty` we define these as `\superscript{\mkern-1.5mu\mathsf{T}\mkern-1.5mu}}` and `\superscript{\mkern-1.5mu\mathsf{H}\mkern-1.5mu}}` respectively. We remove half a thinspace (`\!`=-3.0mu) on each side of the letter to improve spacing.

## 2024-04-02

- Added missing letter-like symbols (now complete)

## 2024-03-08

- Revamped the installation script, now with `argparse`.
- Refactored the installation procedure. Now expects folders with `.tsv` files as input.
- Split custom icons into separate files, according to Unicode block.

## 2024-02-27

- Added italic and bold italic Greek variants to `unicode-symbols.sty`.
- Added missing "variant" Greek symbols such as `𝛡` (`\bfvarpi`)

## 2024-02-26

Main work was refactoring the `unicode-symbols` package. It is now located in the `latex-package` directory.
Additionally, a main achievement is the novel code for sub- and superscripts which automatically combines multiple sub- and superscripts into a single command.

For example, `$xᵢⱼ$` will render identically to `$x_{ij}$` ($x_{ij}$).

## 2024-01-23

Finally, merged a dev branch into main.

⚠️ Added `unicode-symbols.sty` which provides a subset of the Unicode symbols for usage with `pdflatex`. ⚠️

- Revamped the generation script
- renamed `.csv` files to `.tsv`, since we use tabs as separators
- added `custom_icons.tsv` with additional Unicode icons
- added `custom_symbols.tsv` with additional Unicode symbols
  - DIGIT variants
    - circled numbers ①, ②, ③, … (`\o1`, `\o2`, … `\o20`)
    - bold digits 𝟎, 𝟏, 𝟐, … (`\bf0`, `\bf1`, … `\bf9`)
    - double-struck digits 𝟘, 𝟙, 𝟚, … (`\bb0`, `\bb1`, … `\bb9`)
    - sans-serif digits 𝟢, 𝟣, 𝟤, … (`\sans0`, `\sans01`, … `\sans9`)
    - bold sans-serif digits 𝟬, 𝟭, 𝟮, … (`\bsans0`, `\bsans1`, … `\bsans9`)
    - typewriter (monospaced) digits 𝟶, 𝟷, 𝟸, … (`\tt0`, `\tt1`, … `\tt9`)
    - digits with stop ⒈, ⒉, ⒊, … (`\1.`, `\2.`, … `\20.`)
    - parenthesized digits ⑴, ⑵, ⑶… (`\(1)`, `\(2)`, … `\(20)`)
  - LETTER variants
    - small capital letters ᴀ, ʙ, ᴄ, … (`\scA`, `\scB`, … `\scZ`)
    - circled uppercase letters Ⓐ, Ⓑ, Ⓒ, … (`\oA`, `\oB`, … `\oZ`)
    - circled lowercase letters ⓐ, ⓑ, ⓒ, … (`\oa`, `\ob`, … `\oz`)
    - parenthesized Latin letters ⒜, ⒝, ⒞, … (`\a`, `\b`, … `\z`)
  - Roman numerals
    - uppercase Roman numerals Ⅰ, Ⅱ, Ⅲ, … (`\RM1`, `\RM2`, … `\RM1000`)
    - lowercase Roman numerals ⅰ, ⅱ, ⅲ, … (`\rm1`, `\rm2`, … `\rm1000`)
  - Additional Aliases from existing Unicode characters
    - ✅ (`\CMARK`), ❌ (`\XMARK`)
    - ‖ (`\|`)
    - ﹢ (`\+`), ﹣ (`\-`), (unary plus/minus)
    - Small Form Variants
    - Full width variants: `，` (`\,`, replace `$,\,$`), `：` (`\:`, replaces `$\colon$`), `；` (`\;`, replaces `$;\,$`)
    - etc.
- Added extraction code for complete Unicode database for future work.

Ideas for future work:

- Support an AutoKey alternative that works with Wayland.
- It would be really nice to have something similar to language server protocol for these Unicode expansion,
  facilitating auto-completion and discovery.
- Auto-generate the `unicode-symbols.sty` file from the Unicode database.
- Allow installing subset of Unicode symbols, e.g. only math symbols, or only arrows, etc.
  - In particular "basic plane" symbols, since overleaf.com only supports those.

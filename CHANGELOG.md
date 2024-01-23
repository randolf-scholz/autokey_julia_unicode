# CHANGELOG

## 2024-01-23

Finally merged a dev branch into main.

⚠️ Added `unicode-symbols.sty` which provides a subset of the unicode symbols for usage with `pdflatex`. ⚠

- Revamped the generation script
- renamed `.csv` files to `.tsv`, since we use tabs as separators
- added `custom_icons.tsv` with additional unicode icons
- added `custom_symbols.tsv` with additional unicode symbols
  - DIGIT variants
    - circled numbers ①,②,③,… (`\o1`, `\o2`,  … `\o20`)
    - bold digits 𝟎,𝟏,𝟐,… (`\bf0`, `\bf1`, … `\bf9`)
    - double-struck digits 𝟘,𝟙,𝟚,… (`\bb0`, `\bb1`, … `\bb9`)
    - sans-serif digits 𝟢,𝟣,𝟤,… (`\sans0`, `\sans01`, … `\sans9`)
    - bold sans-serif digits 𝟬,𝟭,𝟮,… (`\bsans0`, `\bsans1`, … `\bsans9`)
    - typewriter (monospace) digits 𝟶,𝟷,𝟸,… (`\tt0`, `\tt1`, … `\tt9`)
    - digits with stop ⒈,⒉,⒊,… (`\1.`, `\2.`, … `\20.`)
    - parenthesized digits ⑴, ⑵, ⑶… (`\(1)`, `\(2)`, … `\(20)`)
  - LETTER variants
    - small capital letters ᴀ,ʙ,ᴄ,… (`\scA`, `\scB`, … `\scZ`)
    - circled uppercase letters Ⓐ,Ⓑ,Ⓒ,… (`\oA`, `\oB`, … `\oZ`)
    - circled lowercase letters ⓐ,ⓑ,ⓒ,… (`\oa`, `\ob`, … `\oz`)
    - parenthesized latin letters ⒜, ⒝, ⒞, … (`\a`, `\b`, … `\z`)
  - Roman Numerals
    - uppercase roman numerals Ⅰ, Ⅱ, Ⅲ,… (`\RM1`, `\RM2`, … `\RM1000`)
    - lowercase roman numerals ⅰ, ⅱ, ⅲ, … (`\rm1`, `\rm2`, … `\rm1000`)
  - Additional Aliases from existing unicode characters
    - ✅ (`\CMARK`), ❌ (`\XMARK`)
    - ‖ (`\|`)
    - ﹢ (`\+`), ﹣ (`\-`), (unary plus/minus)
    - Small Form Variants
    - Fullwidth variants: `，` (`\,`, replace `$,\,$`), `：` (`\:`, replaces `$\colon$`), `；` (`\;`, replaces `$;\,$`)
    - etc.
- Added extraction code for complete unicode database for future work.

Ideas for future work:

- support an autokey alternative that works with wayland.
- It would be really nice to have something similar to language server protocol for these unicode expansion,
  facilitating auto-completion and discovery.
- autogenerate the `unicode-symbols.sty` file from the unicode database.
- Allow installing subset of unicode symbols, e.g. only math symbols, or only arrows, etc.
  - in particular "basic plane" symbols, since overleaf.com only supports those.

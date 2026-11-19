# Choosing and Checking Fonts

Open the [Unicode font demo](demo.md) as plain text in your preferred editor and select the font you
want to inspect. Check for missing glyphs, misplaced combining marks, and
inconsistent character widths. A Markdown preview may use a different font from
the editor, so inspect the source text when evaluating your editor's font.

You can also copy the [character samples](demo.md#character-samples) into
[Programming Fonts](https://www.programmingfonts.org/) to compare fonts in the
browser. Check the result in your own editor as well.

See the [font recommendations](../README.md#choosing-a-font) for suggested
monospaced fonts for mathematical code and notes.

The comparison results below record previous
observations and may vary with the font version, editor, and fallback fonts.

## Checking installed font coverage

On Linux, use `fc-list` from [Fontconfig](https://fontconfig.pages.freedesktop.org/fontconfig/fontconfig-user.html)
to list installed fonts containing a character. Supply its hexadecimal Unicode
code point without the `U+` prefix. For example, `𝛼` (mathematical italic small
alpha) is U+1D6FC; ordinary `α` is a different character, U+03B1.

```bash
# All installed font faces containing 𝛼 (U+1D6FC).
fc-list ':charset=1d6fc' family style file

# Only faces in the JuliaMono family containing that character.
fc-list 'JuliaMono:charset=1d6fc' family style file

# Restrict the query to a style as well.
fc-list 'JuliaMono:style=Regular:charset=1d6fc' family style file

# Faces containing ALL of these: 𝐀, 𝑥, 𝔸, 𝛼.
fc-list ':charset=1d400 1d465 1d538 1d6fc' family style file
```

Replace `JuliaMono` with the installed family name. Output identifies matching
families, styles, and font files; no output means no installed face matches all
the requested properties. To distinguish a missing font from a missing glyph,
list its installed faces without the character filter:

```bash
fc-list 'JuliaMono' family style file
```

For a yes/no check in Bash, use `--quiet`, which returns exit status 1 when
there is no match (`fc-list` normally succeeds even with no output):

```bash
if fc-list --quiet 'JuliaMono:charset=1d6fc'; then
    echo 'An installed JuliaMono face contains 𝛼.'
else
    echo 'No installed JuliaMono face contains 𝛼.'
fi
```

`fc-match` finds the closest available font and can return a substitute, so its
output alone does not prove that the requested font contains the character.
These queries check encoded character coverage; use the [demo](demo.md) to judge
appearance, spacing, and combining-mark placement in your editor.

## What to inspect

### Greek tests

We check whether Greek characters are supported, in particular also the variants of `ε`, `θ`, `ϑ`, `ϰ`, `ϖ`, `ϱ`, `ς`,
`φ`.

### Combining character tests

We check whether combining characters are supported, such as`\vec`, `\hat`, `\bar`, `\dot`, `\ddot`, `\tilde`.
We inspect visual quality:

- Are the combining characters neatly placed?
- Do they work well with capital and Greek letters?

### Mono-spacing tests

1. Arrows: We compare rows of 12 arrows `\rightarrow`, `\mapsto`, `\leadsto` and `\leftrightarrow` against
   rows of 12 of the `long` versions of these arrows in the [demo](demo.md#character-samples).
   In this test, we value consistency:

   - Full marks `✅️✅️` if all long arrows are the same length and all short arrows are the same length.
   - Half marks `✅️` if there are at most 3 different lengths.
   - No marks `❌️` if there are more than 3 different lengths.

2. Dashes: We compare the lengths of 12x`\emdash` against 6x `\twoemdash` and 4x`\threeemdash`.
3. Operators: We compare the character `\bigodot` against `\bigoplus` and `\bigotimes`.
4. Greek subscripts: We test whether Greek subscripts `ᵦ`, `ᵧ`, etc. are monospaced.
5. Combining: Whether combining characters are monospaced.
6. Character variants: Whether the character variants `𝐍`, `𝑁`, `𝑵`, `𝙽`, `ℕ`, `𝒩`, `𝓝`, `𝔑`, `𝕹` are monospaced.
7. Math-monospacing: We check whether mathematical symbols are monospaced, for instance integrals.

## Results

| Font           | Greek | comb.-Latin | comb.-Greek | double-struck | Latin variants | combining | bigodot | arrow | dash | sub | coverage |
|----------------|-------|-------------|-------------|---------------|----------------|-----------|---------|-------|------|-----|----------|
| Code New Roman | ✅️    | ✅️✅️        | ❌️          | neat          | ❌️             | ❌️        | ❌️      | ❌️    | ❌️   | ✅️  | ❓️       |
| DejaVu Mono    | ✅️✅️  | ✅️✅️        | ❌️          | neat          | ❌️             | ❌️        | ❌️      | ✅️    | ❌️   | ❌️  | ❓️       |
| Droid Sans     | ✅️✅️  | ✅️✅️        | ❌️          | neat          | ❌️             | ❌️        | ❌️      | ✅️    | ❌️   | ❌️  | ❓️       |
| FairFax        | ✅️✅️  | ✅️          | ✅️          | neat          | ❌️             | ✅️        | ✅️      | ✅️✅️  | ❌️   | ✅️  | ❓️       |
| FairFax Hax HD | ✅️✅️  | ✅️          | ✅️          | ugly          | ❌️             | ✅️        | ✅️      | ✅️✅️  | ✅️   | ✅️  | ❓️       |
| FairFax HD     | ✅️✅️  | ∅           | ∅           | ugly          | ❌️             | ✅️        | ✅️      | ✅️    | ❌️   | ✅️  | ❓️       |
| Iosevka        | ✅️✅️  | ✅️✅️        | ✅️          | neat          | ❌️             | ❌️        | ✅️      | ❌️    | ❌️   | ❌️  | ❓️       |
| JetBrains Mono | ✅️✅️  | ✅️✅️        | ✅️          | neat          | ❌️             | ❌️        | ❌️      | ✅️    | ❌️   | ❌️  | ❓️       |
| JuliaMono      | ✅️✅️  | ✅️✅️        | ✅️✅️        | ugly          | ✅️             | ✅️        | ✅️      | ✅️✅️  | ❌️   | ✅️  | ❓️       |
| Noto Mono      | ❌️    | ✅️✅️        | ✅️          | neat          | ❌️             | ❌️        | ❌️      | ❌️    | ✅️   | ✅️  | ❓️       |
| Unifont EX     | ✅️✅️  | ✅️✅️        | ✅️✅️        | neat          | ❌️             | ✅️        | ✅️      | ✅️✅️  | ❌️   | ✅️  | ❓️       |

## References

- <https://devfonts.gafi.dev/>
- <https://juliamono.netlify.app/>
- <https://mono-math.netlify.app/>
- <https://www.programmingfonts.org/>
- <https://github.com/kreativekorp/open-relay/tree/master/FairfaxHD>

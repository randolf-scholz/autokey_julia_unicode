# Monospace Font Recommandations

## Tests

Using <https://www.programmingfonts.org/>, several fonts were inspected. Several considerations were made:

### greek tests

We check whether greek characters are supported, in particular also the variants of `ε`, `θ`, `ϑ`, `ϰ`, `ϖ`, `ϱ`, `ς`, `φ`.

### combining character tests

We check whether combining characters are supported, such as`\vec`, `\hat`, `\bar`, `\dot`, `\ddot`, `\tilde`.
We inspect visual quality:

- Are the combining characters neatly placed?
- Do they work well with capital and greek letters?

### mono-spacing tests

1. arrows:  We compare the lengths of 16x arrows `\rightarrow`, `\mapsto`, `\leadsto` and `\leftrightarrow` against the lengths of 8x of the `long` versions of these arrows.
   In this test, we value consistency:
   - Full marks `✅✅` if all long arrows are the same length and all short arrows are the same length.
   - Half marks `✅` if there are at most 3 different lengths.
   - No marks `❌` if there are more than 3 different lengths.
2. dashes: We compare the lengths of 12x`\emdash` against 6x `\twoemdash` and 4x`\threeemdash`.
3. bigodot: We compare the character `\bigodot` against `\bigoplus` and `\bigotimes`.
4. greek subscripts: We test whether greek subscripts `ᵦ`, `ᵧ`, etc. are mono-spaced.
5. combining: Whether combining characters are mono-spaced.
6. character variants: Whether the character variants `𝐍`, `𝑁`, `𝑵`, `𝙽`, `ℕ`, `𝒩`, `𝓝`, `𝔑`, `𝕹` are mono-spaced.
7. math-monospacing: We check whether mathematical symbols are mono-spaced, for instance integrals.

## Results

| Font           | greek | comb.-latin | comb.-greek | double-struck | latin variants | combining | bigodot | arrow | dash | sub | coverage |
|----------------|-------|-------------|-------------|---------------|----------------|-----------|---------|-------|------|-----|----------|
| Code New Roman | ✅     | ✅✅          | ❌           | neat          | ❌              | ❌         | ❌       | ❌     | ❌    | ✅   | ?        |
| DejaVu Mono    | ✅✅    | ✅✅          | ❌           | neat          | ❌              | ❌         | ❌       | ✅     | ❌    | ❌   | ?        |
| Droid Sans     | ✅✅    | ✅✅          | ❌           | neat          | ❌              | ❌         | ❌       | ✅     | ❌    | ❌   | ?        |
| FairFax        | ✅✅    | ✅           | ✅           | neat          | ❌              | ✅         | ✅       | ✅✅    | ❌    | ✅   | ?        |
| FairFax Hax HD | ✅✅    | ✅           | ✅           | ugly          | ❌              | ✅         | ✅       | ✅✅    | ✅    | ✅   | ?        |
| FairFax HD     | ✅✅    | ∅           | ∅           | ugly          | ❌              | ✅         | ✅       | ✅     | ❌    | ✅   | ?        |
| Iosevka        | ✅✅    | ✅✅          | ✅           | neat          | ❌              | ❌         | ✅       | ❌     | ❌    | ❌   | ?        |
| JetBrains Mono | ✅✅    | ✅✅          | ✅           | neat          | ❌              | ❌         | ❌       | ✅     | ❌    | ❌   | ?        |
| JuliaMono      | ✅✅    | ✅✅          | ✅✅          | ugly          | ✅              | ✅         | ✅       | ✅✅    | ❌    | ✅   | ?        |
| Noto Mono      | ❌     | ✅✅          | ✅           | neat          | ❌              | ❌         | ❌       | ❌     | ✅    | ✅   | ?        |
| Unifont EX     | ✅✅    | ✅✅          | ✅✅          | neat          | ❌              | ✅         | ✅       | ✅✅    | ❌    | ✅   | ?        |

## Test document

```tex
% special characters
â é ù ï ø ç Ã Ē Æ œ

% combining characters
x⃗, ȳ, z̃, ẋ, ÿ, z⃛, x̂, y᪲
X⃗, Ȳ, Z̃, Ẋ, Ÿ, Z⃛, X̂, Y᪲
μ⃗, ν̄, ξ̃, μ̇, ν̈, ξ⃛, μ̂, ν᪲
Μ⃗, Ν̄, Ξ̃, Μ̇, Ν̈, Ξ⃛, Μ̂, Ν᪲

% character variants
| char | bf | it | bi | tt | bb | scr | bscr | frak | bfrak |
|---|---|---|---|---|---|---|---|---|---|
| N | 𝐍 | 𝑁 | 𝑵 | 𝙽 | ℕ | 𝒩 | 𝓝 | 𝔑 | 𝕹 |
| Z | 𝐙 | 𝑍 | 𝒁 | 𝚉 | ℤ | 𝒵 | 𝓩 | ℨ | 𝖅 |
| Q | 𝐐 | 𝑄 | 𝑸 | 𝚀 | ℚ | 𝒬 | 𝓠 | 𝔔 | 𝕼 |
| R | 𝐑 | 𝑅 | 𝑹 | 𝚁 | ℝ | ℛ | 𝓡 | ℜ | 𝕽 |
| C | 𝐂 | 𝐶 | 𝑪 | 𝙲 | ℂ | 𝒞 | 𝓒 | ℭ | 𝕮 |
| L | 𝐋 | 𝐿 | 𝑳 | 𝙻 | 𝕃 | ℒ | 𝓛 | 𝔏 | 𝕷 |

% greek
Α, Β, Γ, Δ, Ε, Ζ, Η, Θ, Ι, Κ, Λ, Μ, Ν, Ξ, Ο, Π, Ρ, Σ, Τ, Υ, Φ, Χ, Ψ, Ω
α, β, γ, δ, ϵ, ζ, η, θ, ι, κ, λ, μ, ν, ξ, ο, π, ρ, σ, τ, υ, ϕ, χ, ψ, ω
            ε        ϑ,    ϰ,                ϖ, ϱ, ς,       φ,

% mono-space test: math
∑∑∑∑∑∑∑∑∑∑∑∑
∏∏∏∏∏∏∏∏∏∏∏∏
∫∫∫∫∫∫∮∮∮∮∮∮
∬∬∬∬∬∬∯∯∯∯∯∯
∭∭∭∭∭∭∰∰∰∰∰∰
⋀⋀⋀⋀⋀⋀⋀⋀⋀⋀⋀⋀
⋁⋁⋁⋁⋁⋁⋁⋁⋁⋁⋁⋁
⋂⋂⋂⋂⋂⋂⋂⋂⋂⋂⋂⋂
⋃⋃⋃⋃⋃⋃⋃⋃⋃⋃⋃⋃
⨁⨁⨁⨁⨁⨁⨁⨁⨁⨁⨁⨁
⨂⨂⨂⨂⨂⨂⨂⨂⨂⨂⨂⨂

% bigodot
⨁⨂⨀

% mono-space test: arrows
→→→→→→→→→→→→→→→→
↔↔↔↔↔↔↔↔↔↔↔↔↔↔↔↔
↦↦↦↦↦↦↦↦↦↦↦↦↦↦↦↦
⇝⇝⇝⇝⇝⇝⇝⇝⇝⇝⇝⇝⇝⇝⇝⇝
⟶⟶⟶⟶⟶⟶⟶⟶
⟷⟷⟷⟷⟷⟷⟷⟷
⟼⟼⟼⟼⟼⟼⟼⟼
⟿⟿⟿⟿⟿⟿⟿⟿

% mono-space test: dash
12x emdash: ————————————
6x2 emdash: ⸺⸺⸺⸺⸺⸺
4x3 emdash: ⸻⸻⸻⸻

% mono-space test: greek subscripts
\textsubscript{α} & — & $_{α}$ & $—$ & \textsuperscript{α} & ᵅ & $^{α}$ & $ᵅ$ \\
\textsubscript{β} & ᵦ & $_{β}$ & $ᵦ$ & \textsuperscript{β} & ᵝ & $^{β}$ & $ᵝ$ \\
\textsubscript{γ} & ᵧ & $_{γ}$ & $ᵧ$ & \textsuperscript{γ} & ᵞ & $^{γ}$ & $ᵞ$ \\
\textsubscript{δ} & — & $_{δ}$ & $—$ & \textsuperscript{δ} & ᵟ & $^{δ}$ & $ᵟ$ \\
\textsubscript{ε} & — & $_{ε}$ & $—$ & \textsuperscript{ε} & ᵋ & $^{ε}$ & $ᵋ$ \\
\textsubscript{θ} & — & $_{θ}$ & $—$ & \textsuperscript{θ} & ᶿ & $^{θ}$ & $ᶿ$ \\
\textsubscript{ι} & — & $_{ι}$ & $—$ & \textsuperscript{ι} & ᶥ & $^{ι}$ & $ᶥ$ \\
\textsubscript{υ} & — & $_{υ}$ & $—$ & \textsuperscript{υ} & ᶹ & $^{υ}$ & $ᶹ$ \\
\textsubscript{φ} & ᵩ & $_{φ}$ & $ᵩ$ & \textsuperscript{φ} & ᵠ & $^{φ}$ & $ᵠ$ \\
\textsubscript{χ} & ᵪ & $_{χ}$ & $ᵪ$ & \textsuperscript{χ} & ᵡ & $^{χ}$ & $ᵡ$ \\
\textsubscript{ϱ} & ᵨ & $_{ϱ}$ & $ᵨ$ & \textsuperscript{ϱ} & — & $^{ϱ}$ & $—$ \\
```

## References

- <https://devfonts.gafi.dev/>
- <https://juliamono.netlify.app/>
- <https://mono-math.netlify.app/>
- <https://www.programmingfonts.org/>
- <https://github.com/kreativekorp/open-relay/tree/master/FairfaxHD>

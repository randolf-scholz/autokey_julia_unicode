# MathJax Unicode Support

`\math-[it, sf, bb, frak, cal, scr]` families are directly translated. The characters can be rendered slightly differently though.

- Latex: $\texttt{D}\mathit{D}\mathbf{D}\mathsf{D}\mathbb{D}\mathfrak{D}\mathcal{D}\mathscr{D}$
- Unicode: $𝙳𝐷𝐃𝖣𝔻𝔇𝓓𝒟$, additional variants: $𝑫𝗗𝘿𝘋$

we can use `sans`-family for upright characters:

- LaTeX: $\int f(x)\, {\rm d}x$
- Unicode: $∫f(x)\, 𝖽x$

Super / sub-scripts are rendered differently:

- LaTeX: $x_t \in \mathbb{R}^2$
- Unicode: $xₜ ∈ ℝ²$

Binary relations have the correct spacing:

- LaTeX:   $\alpha\simeq\beta$
- Unicode: $α≃β$

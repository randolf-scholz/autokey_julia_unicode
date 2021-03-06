# MathJax Unicode Support

`\math-[it, sf, bb, frak, cal, scr]` families are directly translated. The characters can be rendered slightly differently though.

- Latex: $\texttt{D}\mathit{D}\mathbf{D}\mathsf{D}\mathbb{D}\mathfrak{D}\mathcal{D}\mathscr{D}$
- Unicode: $π³π·ππ£π»πππ$, additional variants: $π«ππΏπ$

we can use `sans`-family for upright characters:

- LaTeX: $\int f(x)\, {\rm d}x$
- Unicode: $β«f(x)\, π½x$

Super / sub-scripts are rendered differently:

- LaTeX: $x_t \in \mathbb{R}^2$
- Unicode: $xβ β βΒ²$

Binary relations have the correct spacing:

- LaTeX:   $\alpha\simeq\beta$ 
- Unicode: $Ξ±βΞ²$

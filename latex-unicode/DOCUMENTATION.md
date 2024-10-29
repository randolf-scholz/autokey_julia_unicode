# Documentation

Font family providers:

## Builtin font-families

- `\mathrm`
- `\mathit`
- `\mathsf`
- `\mathbf`
- `\mathtt`
- `\mathcal`

extra packages required for:

- `\mathfrak`
- `\mathscr`
- `\mathbb`

## Bold symbols

If we want bold symbols, in particular also: greek+bold, italic+bold, etc. There are several ways to do this.

## Other Builtin modifiers

See section 16.4-16.5 Latex2e documentation. (math mode only!)

1. `\acute`
2. `\bar`
3. `\breve`
4. `\check`
5. `\ddot`
6. `\dot`
7. `\grave`
8. `\hat`
9. `\tilde`
10. `\vec`
11. `\overline`
12. `\underline`
13. `\widehat`
14. `\widetilde`
15. `\overbrace`
16. `\underbrace`
17. `\mathring`

Additionally, the (undocumented?) commands:

- `\overrightarrow`
- `\overleftarrow`

## Consistent modifier names

There are some modifiers that are not consistent in their naming.

- raised/lowered.
- flipped/turned/mirrored/rotated/down/inverted/reversed
- "reversed": **always** a horizontal mirror symmetry.
- "turned": **always** a 180° rotation.
- "inverted": can be either a vertical mirror symmetry OR a 180° rotation.
  - `¿` (U+00BF: Inverted Question Mark) is a 180° rotation of `?` (U+003F: Question Mark),
    instead of a vertical mirror symmetry.
  - `ʀ` (U+0280: Latin Letter Small Capital R) has two variants:
    - `ʁ` (U+0281: Latin Letter Small Capital Inverted R) is a vertical mirror symmetry.
    - `ᴚ` (U+1D1A: Latin Letter Small Capital Turned R) which is a 180° rotation

1. Create canonical names for the various euclidean transformations.
2. Characters that are symmetric themselves should have aliases for the various transformations.

Examples:

- `¡` (U+00A1: Inverted Exclamation Mark) `\exclamdown`
- `ɥ` (U+0265: Turned H)

# Custom Unicode Icons

These tabular separated value (TSV) files define:

1. Custom abbreviations for some Unicode characters that differ from the ones used in Julia.
2. Custom icons (Unicode characters) that are not included in the standard Julia Unicode set.

Moreover, the `dingbats` and `emoticons` files include special versions that consist of the character itself plus a variation selector (VS16 `U+FE0F`) to enforce emoji-style rendering.

This ensures that glyphs like `✅`, `❌`, `⚠` or `♻` are displayed as `✅️`, `❌️`, `⚠️` or `♻️`, respectively, in applications that support emoji presentation.

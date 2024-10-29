# How to progress

- Need to automate the process of adding symbols.
- Need a database of symbols, together with providers.
  - For a given symbol, there may be multiple providers, such as `stix`, `amssymb`, etc.
  - Create a table with Unicode-chars, mapping to the providers.

## Header scheme for Database

Create a table with the following headers:

- `ID`: Unicode hexadecimal code.
- `CHAR`: Unicode character.
- `GROUP`: Group of the symbol.
- `NAME`: Name of the symbol. (used to create...)
- `canonical_command`: canonical command which will be assigned by `\newunicodechar`.
  - Example: `\hateq` for `≙`.
- `canonical_type`: canonical type of the symbol (`mathbin`, `mathord`, etc.)
- `providers`: mapping between latex packages and the command that produces the symbol.
  - Maybe just as regular columns...
  - Maybe synthesize from per package tables.
  - Example: `{stix: \hateq, fdsymbol: \wedgeq}`.
  - Default providers: `core`, `ams`, `stix`, `fdsymbol`, `MnSymbol`, etc.
- `type`

## Automating tests

We need to test several things:

- Unicode chars work.
- AutoKey-mappings align with the Unicode chars.
- The symbols are correctly displayed in the pdf.
- The symbols are searchable in the pdf.
- Tests are automated.

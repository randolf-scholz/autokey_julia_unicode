module JuliaIconImportTests

using Test

const ICONS_FILENAME = "icons-julia.tsv"
const IMPORT_JULIA = normpath(joinpath(@__DIR__, "..", "src", "import_julia.jl"))

# Keep the script's @main entry point outside Main during tests.
include(IMPORT_JULIA)

@testset "Julia icon import" begin
    mktempdir() do directory
        output = joinpath(directory, ICONS_FILENAME)
        unicode_data = joinpath(directory, "UnicodeData.txt")
        schema_path = joinpath(directory, "schema.toml")
        write(joinpath(directory, "NameAliases.txt"),
            "# Synthetic aliases\n000A;LINE FEED;control\n000A;LF;abbreviation\n00A6;IGNORED ALIAS;correction\n")
        open(unicode_data, "w") do io
            for (point, name, legacy) in (
                (0x000a, "<control>", "OLD LINE FEED"),
                (0x00a6, "BROKEN BAR", "BROKEN VERTICAL BAR"),
                (0x00a9, "COPYRIGHT SIGN", ""),
                (0x2242, "MINUS TILDE", ""),
                (0x0338, "COMBINING LONG SOLIDUS OVERLAY", "NON-SPACING LONG SLASH OVERLAY"),
                (0xfe00, "VARIATION SELECTOR-1", ""),
                (0x1f600, "GRINNING FACE", ""),
            )
                fields = fill("", 15)
                fields[1] = uppercase(string(point; base=16))
                fields[2] = name
                fields[11] = legacy
                println(io, join(fields, ';'))
            end
        end
        open(schema_path, "w") do io
            TOML.print(io, Dict("format" => Dict("required_columns" => collect(HEADER))))
        end
        symbols = Dict(
            "\\copyright" => "©",
            "\\:copyright:" => "©",
            "\\brokenbar" => "¦",
            "\\hat" => "\u0302",
            "\\grave" => "\u0300",
            "\\acute" => "\u0301",
            "\\enclosecircle" => "\u20dd",
            "\\nbsp" => "\u00a0",
            "\\linefeed" => "\n",
            "\\tab" => "\t",
            "\\carriagereturn" => "\r",
            "\\neqsim" => "≂\u0338",
            "\\varsim" => "≂\ufe00",
            "\\twosim" => "≂≂",
            "\\:grinning:" => "😀",
            "\\unknown" => "\ue001",
        )
        import_icons(output; symbols, unicode_data, schema_path)
        rows = [split(line, '\t') for line in readlines(output)]
        @test rows[1] == [
            "code_points", "chars", "tab_completions", "unicode_name",
        ]
        @test length(rows) == 16 # Two aliases share one row.
        @test all(length(row) == 4 for row in rows)
        by_point = Dict(row[1] => row[2:4] for row in rows[2:end])
        @test by_point["U+000A6"][3] == "Broken Bar"
        @test by_point["U+0000A"][3] == "Line Feed"
        @test by_point["U+000A9"] == [
            "©", "\\:copyright:, \\copyright", "Copyright Sign",
        ]
        @test by_point["U+00300"][1] == "\u0300"
        @test by_point["U+00301"][1] == "\u0301"
        @test by_point["U+00302"][1] == "\u0302"
        @test by_point["U+020DD"][1] == "\u20dd"
        @test by_point["U+000A0"][1] == "\u00a0"
        @test all(isempty(by_point[point][1]) for point in ("U+00009", "U+0000A", "U+0000D"))
        @test by_point["U+02242, U+00338"] == [
            "≂\u0338", "\\neqsim",
            "Minus Tilde, Combining Long Solidus Overlay",
        ]
        @test by_point["U+02242, U+0FE00"][3] == "Minus Tilde, Variation Selector-1"
        @test by_point["U+02242, U+02242"][3] == "Minus Tilde, Minus Tilde"
        @test by_point["U+1F600"][3] == "Grinning Face"
        @test by_point["U+0E001"][3] == ""

        # All aliases from the running REPL must survive the full export, once each.
        import_icons(output; unicode_data, schema_path)
        first_export = read(output)
        rows = [split(line, '\t') for line in readlines(output)[2:end]]
        repl_symbols = merge(
            REPL.REPLCompletions.latex_symbols,
            REPL.REPLCompletions.emoji_symbols,
        )
        @test length(rows) == length(unique(values(repl_symbols)))
        @test issorted([row[1] for row in rows])
        exported = Dict(
            alias => row[2]
            for row in rows for alias in split(row[3], ", ")
        )
        @test exported == repl_symbols
        import_icons(output; unicode_data, schema_path)
        @test read(output) == first_export

        # A name containing the separator must never become multiple list items.
        ambiguous = joinpath(directory, "ambiguous.txt")
        write(ambiguous, replace(read(unicode_data, String), "MINUS TILDE;" => "MINUS, TILDE;"))
        @test_throws AssertionError import_icons(
            joinpath(directory, "ambiguous.tsv"); symbols, unicode_data=ambiguous, schema_path
        )

        # A schema mismatch must be rejected before replacing an existing export.
        @test isnothing(validate_header(schema_path))
        invalid_schema = joinpath(directory, "invalid-schema.toml")
        for order in (
            ["chars", "code_points", "tab_completions", "unicode_name"],
            ["code_points", "chars", "tab_completions"],
            ["code_points", "chars", "tab_completions", "unicode_name", "chars"],
            ["code_points", "chars", "tab_completions", "unicode_name", "notes"],
        )
            schema = TOML.parsefile(schema_path)
            schema["format"]["required_columns"] = order
            open(invalid_schema, "w") do io
                TOML.print(io, schema)
            end
            @test_throws ArgumentError validate_header(invalid_schema)
            @test_throws ArgumentError import_icons(
                output; unicode_data, schema_path=invalid_schema
            )
            @test read(output) == first_export
        end

        # Reject malformed UCD input before overwriting an existing export.
        malformed = joinpath(directory, "malformed.txt")
        write(malformed, "0041;LATIN CAPITAL LETTER A\n")
        @test_throws ArgumentError import_icons(
            output; unicode_data=malformed, schema_path
        )
        @test read(output) == first_export
    end
end

end # module JuliaIconImportTests

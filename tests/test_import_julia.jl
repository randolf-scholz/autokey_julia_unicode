module JuliaIconImportTests

using Test

# Keep the script's @main entry point outside Main during tests.
include(joinpath(@__DIR__, "..", "src", "import_julia.jl"))

@testset "Julia icon import" begin
    mktempdir() do directory
        output = joinpath(directory, "icons.tsv")
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
            "\\:grinning:" => "😀",
            "\\unknown" => "\ue001",
        )
        import_icons(output; symbols)
        rows = [split(line, '\t') for line in readlines(output)]
        @test rows[1] == [
            "code_points", "chars", "tab_completions", "unicode_name",
        ]
        @test length(rows) == 14 # Two aliases share one row.
        @test all(length(row) == 4 for row in rows)
        by_point = Dict(row[1] => row[2:4] for row in rows[2:end])
        @test by_point["U+000A6"][3] == "Broken Bar / Broken Vertical Bar"
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
            "Minus Tilde + Combining Long Solidus Overlay / Non-Spacing Long Slash Overlay",
        ]
        @test by_point["U+1F600"][3] == "Grinning Face"
        @test by_point["U+0E001"][3] == "(No Unicode name)"

        # All aliases from the running REPL must survive the full export, once each.
        import_icons(output)
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
        @test all(!occursin("(No Unicode name)", row[4]) for row in rows)
        import_icons(output)
        @test read(output) == first_export

        # A schema mismatch must be rejected before replacing an existing export.
        @test isnothing(validate_header())
        schema_path = joinpath(directory, "schema.toml")
        for order in (
            ["chars", "code_points", "tab_completions", "unicode_name"],
            ["code_points", "chars", "tab_completions"],
            ["code_points", "chars", "tab_completions", "unicode_name", "chars"],
            ["code_points", "chars", "tab_completions", "unicode_name", "notes"],
        )
            schema = TOML.parsefile(SCHEMA_PATH)
            schema["format"]["required_columns"] = order
            open(schema_path, "w") do io
                TOML.print(io, schema)
            end
            @test_throws ArgumentError validate_header(schema_path)
            @test_throws ArgumentError import_icons(output; schema_path)
            @test read(output) == first_export
        end

        # Reject malformed UCD input before overwriting an existing export.
        malformed = joinpath(directory, "UnicodeData.txt")
        write(malformed, "0041;LATIN CAPITAL LETTER A\n")
        @test_throws ArgumentError import_icons(output; unicode_data=malformed)
        @test read(output) == first_export
    end
end

end # module JuliaIconImportTests

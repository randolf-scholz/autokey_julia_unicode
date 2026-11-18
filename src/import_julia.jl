#!/usr/bin/env julia
# Usage: julia src/export_julia.jl [output.tsv]
import REPL, TOML

const UNICODE_DATA = joinpath(@__DIR__, "..", "third_party", "ucd", "UnicodeData.txt")
const SCHEMA_PATH = joinpath(@__DIR__, "..", "icons", "schema.toml")
const HEADER = ("code_points", "chars", "tab_completions", "unicode_name")
const ICONS_PATH = normpath(joinpath(
    @__DIR__, "..", "icons", "julia_unicode", "icons-$(VERSION).tsv"
))

"""Require the exported header to match the schema's ordered required columns."""
function validate_header(path::AbstractString=SCHEMA_PATH)
    schema = TOML.parsefile(path)
    collect(HEADER) == schema["format"]["required_columns"] || throw(ArgumentError(
        "$path: HEADER must match format.required_columns exactly"
    ))
    return nothing
end

"""Read current and legacy Unicode names from the locally imported UCD."""
function read_unicode_names(path::AbstractString)
    names = Dict{UInt32,String}()
    for (line_number, line) in enumerate(eachline(path))
        isempty(line) && continue
        fields = split(line, ';'; keepempty=true)
        length(fields) == 15 || throw(ArgumentError(
            "$path:$line_number: expected 15 UnicodeData fields"
        ))
        name, legacy = fields[2], fields[11]
        names[parse(UInt32, fields[1]; base=16)] = titlecase(lowercase(
            isempty(legacy) ? name : "$name / $legacy"
        ))
    end
    return names
end

"""
    export_icons(output_path=ICONS_PATH; unicode_data=UNICODE_DATA, schema_path=SCHEMA_PATH)

Export the running Julia version's LaTeX and emoji completions in the icon
schema's column order. The default output is
icons/julia_unicode/icons-<julia-version>.tsv. Default paths are relative to the
repository, independent of the working directory.
"""
function export_icons(
    output_path::AbstractString=ICONS_PATH;
    unicode_data::AbstractString=UNICODE_DATA,
    schema_path::AbstractString=SCHEMA_PATH,
    symbols=merge(
        REPL.REPLCompletions.latex_symbols,
        REPL.REPLCompletions.emoji_symbols,
    ),
)
    validate_header(schema_path)
    names = read_unicode_names(unicode_data)

    # Group aliases for each character or multi-code-point sequence.
    completions = Dict{String,Vector{String}}()
    for (sequence, chars) in symbols
        push!(get!(completions, chars, String[]), sequence)
    end

    open(output_path, "w") do io
        println(io, join(HEADER, '\t'))

        for (chars, sequences) in sort!(collect(completions); by=first)
            points = join((
                "U+" * uppercase(string(UInt32(c); base=16, pad=5))
                for c in chars
            ), ", ")

            # Store replacement text exactly; omit cells that would break TSV records.
            characters = occursin(r"[\t\r\n]", chars) ? "" : chars

            unicode_names = join((
                get(names, UInt32(c), "(No Unicode name)")
                for c in chars
            ), " + ")

            println(io, join((
                points,
                characters,
                join(sort!(sequences), ", "),
                unicode_names,
            ), '\t'))
        end
    end
    return output_path
end

function (@main)(args)
    length(args) <= 1 || error("Usage: julia src/export_julia.jl [output.tsv]")
    output_path = isempty(args) ? ICONS_PATH : only(args)
    export_icons(output_path)
    println("Exported Julia $VERSION icons to $(abspath(output_path))")
    return nothing
end

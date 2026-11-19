#!/usr/bin/env julia
# Usage: julia src/import_julia.jl [output.tsv]
import REPL, TOML

const PROJECT_DIR = normpath(joinpath(@__DIR__, ".."))
const DATA_DIR = joinpath(PROJECT_DIR, "data")

const UNICODE_DATA = joinpath(PROJECT_DIR, "third_party", "ucd", "UnicodeData.txt")
const SCHEMA_PATH = joinpath(DATA_DIR, "schemas", "icons.toml")
const ICONS_PATH = joinpath(DATA_DIR, "icons", "julia", "icons-julia-$(VERSION).local.tsv")
const HEADER = ("code_points", "chars", "tab_completions", "unicode_name")

"""Require the exported header to match the schema's ordered required columns."""
function validate_header(path::AbstractString=SCHEMA_PATH)
    schema = TOML.parsefile(path)
    collect(HEADER) == schema["format"]["required_columns"] || throw(ArgumentError(
        "$path: HEADER must match format.required_columns exactly"
    ))
    return nothing
end

"""Read the first alias for each code point, preserving file order."""
function read_name_aliases(path::AbstractString)
    aliases = Dict{UInt32,String}()
    for (line_number, line) in enumerate(eachline(path))
        line = strip(first(split(line, '#'; limit=2)))
        isempty(line) && continue
        fields = strip.(split(line, ';'; keepempty=true))
        length(fields) == 3 && !isempty(fields[2]) && !isempty(fields[3]) || throw(ArgumentError(
            "$path:$line_number: invalid name alias"
        ))
        get!(aliases, parse(UInt32, fields[1]; base=16), String(fields[2]))
    end
    return aliases
end

"""Read current names, falling back to the first alias for unnamed characters."""
function read_unicode_names(path::AbstractString)
    aliases = read_name_aliases(joinpath(dirname(path), "NameAliases.txt"))
    names = Dict{UInt32,String}()
    for (line_number, line) in enumerate(eachline(path))
        isempty(line) && continue
        fields = split(line, ';'; keepempty=true)
        length(fields) == 15 || throw(ArgumentError(
            "$path:$line_number: expected 15 UnicodeData fields"
        ))
        point = parse(UInt32, fields[1]; base=16)
        name = startswith(fields[2], "<") ? "" : fields[2]
        isempty(name) && (name = get(aliases, point, ""))
        names[point] = titlecase(lowercase(name))
    end
    return names
end

"""
    import_icons(output_path=ICONS_PATH; unicode_data=UNICODE_DATA, schema_path=SCHEMA_PATH)

Import the running Julia version's LaTeX and emoji completions in the icon
schema's column order. The default output is
data/icons/julia/icons-julia-<julia-version>.local.tsv. Default paths are relative to the
repository, independent of the working directory.
"""
function import_icons(
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
    name_separator = ", "

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

            unicode_names = [
                get(names, UInt32(c), "")
                for c in chars
            ]
            @assert !any(name -> occursin(name_separator, name), unicode_names) "Unicode name contains the list separator"

            println(io, join((
                points,
                characters,
                join(sort!(sequences), ", "),
                join(unicode_names, name_separator),
            ), '\t'))
        end
    end
    return output_path
end

function (@main)(args)
    length(args) <= 1 || error("Usage: julia src/import_julia.jl [output.tsv]")
    output_path = isempty(args) ? ICONS_PATH : only(args)
    import_icons(output_path)
    println("Imported Julia $VERSION icons to $(abspath(output_path))")
    return nothing
end

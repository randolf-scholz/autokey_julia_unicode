#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12.3"
# ///
"""Generate phrases for autokey."""

import argparse
import csv
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from collections import Counter, defaultdict
from collections.abc import Generator, Sequence
from pathlib import Path
from typing import Any, Final, Literal, NamedTuple, Self, TypeGuard

LOGGER = logging.getLogger(__name__)
BUILD_DIR: Final[Path] = Path(__file__).resolve().parents[1] / "build"
type JSON = dict[str, Any]


def check_autokey_version() -> None:
    """Require system AutoKey >=0.96.0 when its version can be determined."""
    for command in ("autokey-gtk", "autokey-qt"):
        # Use the system search path so a virtual environment cannot shadow AutoKey.
        executable = shutil.which(command, path=os.defpath)
        if executable is None:
            continue
        try:
            result = subprocess.run(
                [executable, "--version"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        match = re.search(r"\b(\d+)\.(\d+)\.(\d+)\b", result.stdout)
        if match is None:
            continue
        if tuple(map(int, match.groups())) < (0, 96, 0):
            sys.exit(f"AutoKey >=0.96.0 is required; found {match[0]}.")
        LOGGER.info("Detected AutoKey %s (%s).", match[0], executable)
        return

    LOGGER.warning(
        "Could not determine the system AutoKey version; continuing. "
        "AutoKey >=0.96.0 is required."
    )


class Glyph(str):
    """Character type."""

    def __new__(cls, value: str) -> Self:
        if not is_glyph(value):
            raise ValueError(f"{value!r} is not a valid character.")
        return super().__new__(cls, value)


def is_glyph(s: object, /) -> TypeGuard[Glyph]:
    """Check whether string is a single character."""
    return isinstance(s, str) and (
        len(s) == 1
        or (
            len(s) == 2
            and (is_variation_selector(s[1]) or is_combining_character(s[1]))
        )
    )


class CodePoint(str):
    """Unicode code type (like U+)."""

    PATTERN = re.compile(r"U\+[0-9A-F]{4,6}")
    """Regex pattern for unicode codes."""

    def __new__(cls, value: str) -> Self:
        if not is_codepoint(value):
            raise ValueError(f"{value!r} is not a valid unicode code.")
        return super().__new__(cls, value)

    @property
    def hex(self) -> int:
        return int(self[2:], 16)  # ruff: ignore[FURB166]


def is_codepoint(s: object, /) -> TypeGuard[CodePoint]:
    """Check whether string is a unicode-code (like U+0000A)."""
    return isinstance(s, str) and CodePoint.PATTERN.fullmatch(s) is not None


def parse_codepoints(s: str, /) -> list[CodePoint]:
    """Parse a string of the form 'U+0000A + U+0000B' into a list of CodePoints."""
    codepoints: list[CodePoint] = [CodePoint(code.strip()) for code in s.split(" + ")]
    # simplify code points by stripping leading zeros, format as U+XXXX
    return [CodePoint(f"U+{code.hex:04X}") for code in codepoints]


class Abbreviation(str):
    """Abbreviation type."""

    PATTERN = re.compile(r"\x5C[\x21-\x7E]+\x20")
    """Regex pattern for abbreviations start with backslash (5C) and end in space (20)."""

    def __new__(cls, value: str) -> Self:
        if not is_abbreviation(value):
            raise ValueError(
                f"{value!r} is not a valid abbreviation."
                "\nAbbrevations must begin with a backslash and terminate with a space."
                "\nInside the abbrevations only the printable ascii characters x21-x7e are allowed,"
                " except backslash x5C."
            )
        return super().__new__(cls, value)


def is_abbreviation(s: object, /) -> TypeGuard[Abbreviation]:
    """Check if string is a valid abbreviation.

    Abbreviations must begin with a backslash followed by one or more
    legal characters and terminate with a single space.
    """
    return isinstance(s, str) and Abbreviation.PATTERN.fullmatch(s) is not None


def is_variation_selector(s: str, /) -> bool:
    """Check whether string is a variation selector."""
    return len(s) == 1 and "\ufe00" <= s <= "\ufe0f"


def is_combining_character(s: str, /) -> bool:
    """Check whether string is a combining character."""
    return len(s) == 1 and "\u0300" <= s <= "\u036f"


def as_hex(s: str, /) -> str:
    """Convert string to hex representation."""
    return str([f"U+{ord(c):04X}" for c in s])


def make_abbreviations(raw_data: str, /) -> list[Abbreviation]:
    """Create the abbreviation list from the raw data."""
    abbreviations: list[Abbreviation] = []

    if not raw_data:
        return abbreviations

    for raw_abb in raw_data.split(", "):
        abb = Abbreviation(raw_abb + " ")  # add single trailing space
        abbreviations.append(abb)

    return abbreviations


def str_to_codepoints(s: str, /) -> list[CodePoint]:
    r"""Convert a string to a list of code points.

    Example:
        >>> str_to_codepoints("✅️")
        ['U+2705', 'U+FE0F']
    """
    return [CodePoint(f"U+{ord(c):04X}") for c in s]


SEND_MODES: Final[dict[int, str]] = {
    0: r"<ctrl>+v",
    1: r"<ctrl>+<shift>+v",
    2: r"<shift>+<insert>",
}
DEFAULT_QUESTION = "Please pick one of the following:"


def query_choice[T](
    question: str = DEFAULT_QUESTION,
    *,
    choices: list[T] | dict[int, T],
    default: int | None = 0,
) -> T:
    """Ask the user to pick an option."""
    options = choices if isinstance(choices, dict) else dict(enumerate(choices))

    if default is not None:
        assert default in options, f"Default {default} not in {options}"

    while True:
        try:
            print(question)
            for i, option in options.items():
                print(f"{i:3d}. {option!r}")
            user_choice = input(f"Enter integer (default: {default}): ")
        except (KeyboardInterrupt, SystemExit):
            print("Operation aborted. Exiting.")
            sys.exit(0)
        try:
            if user_choice == "" and default is not None:
                return options[default]
            return options[int(user_choice)]
        except (KeyError, ValueError):
            print("Did not understand input.")


class UnprocessedSample(NamedTuple):
    """Named tuple for unprocessed unicode samples."""

    ucode: str
    char: str
    abbreviations: str
    description: str

    def __repr__(self) -> str:
        char, ucode, abbrevations = self.char, self.ucode, self.abbreviations
        return f"{char=!r}: {ucode=!r}  {abbrevations=!r}"


class UnicodeSample(NamedTuple):
    """Named tuple for unicode samples."""

    ucode: list[CodePoint]
    glyph: Glyph
    abbreviations: list[Abbreviation]
    description: str

    @property
    def name(self) -> str:
        """Filename stem shared by the phrase and its metadata."""
        return "_".join(self.ucode)

    def __repr__(self) -> str:
        char, ucode, abbrevations = self.glyph, self.ucode, self.abbreviations
        return f"{ucode}: {char!r}  {abbrevations=!s}"


class PhraseCreationResult(NamedTuple):
    """Result of creating an AutoKey phrase."""

    status: Literal["created", "skipped_duplicate"]
    name: str


HEADER = (
    "Code point(s)",
    "Character(s)",
    "Tab completion sequence(s)",
    "Unicode name(s)",
)
"""Header for the unicode samples."""


def read_row(row: Sequence[str] | Generator[str]) -> UnprocessedSample:
    """Read a row from the tsv file."""
    row = list(row)
    try:
        return UnprocessedSample(*row)
    except TypeError as exc:
        exc.add_note(f"Failed to parse row with {len(row)} elements. {row} .\n")
        for i, col in enumerate(row):
            exc.add_note(f"Column {i}: {col!r}.")
        raise


def load_icons(fname: str | Path, /) -> list[UnprocessedSample]:
    """Load the icons from the tsv file."""
    LOGGER.info("Parsing %s", fname)

    with open(fname, "r", encoding="utf8") as tsv_file:
        # scraped from https://docs.julialang.org/en/v1/manual/unicode-input/
        reader_obj = csv.reader(tsv_file, delimiter="\t", quotechar=None)
        items: list[list[str]] = list(reader_obj)

    header = items[0]
    data = items[1:]

    if missing_cols := set(HEADER) - set(header):  # pyright: ignore[reportOperatorIssue]
        raise ValueError(f"Missing columns: {missing_cols}")

    mask = [idx for idx, col in enumerate(header) if col in HEADER]

    if mask == [0, 1, 2, 3]:
        return [read_row(row[:4]) for row in data]
    return [read_row(row[i] for i in mask) for row in data]


def process_icons(data: list[UnprocessedSample], /) -> list[UnicodeSample]:
    """Validate samples, skipping unsupported glyphs and missing abbreviations."""
    samples: list[UnicodeSample] = []
    LOGGER.info("Pre-Processing %d items.", len(data))
    skipped: list[tuple[UnprocessedSample, str]] = []  # items

    for item in data:
        ucode, char, raw_abb, description = item
        parsed_ucodes = parse_codepoints(ucode)

        # guard against invalid character
        if not is_glyph(char):
            LOGGER.debug("Invalid character: %s=%s", item.ucode, item.char)
            skipped.append(
                (
                    item,
                    f"Invalid character {char!r}={as_hex(char)}",
                )
            )
            continue

        # guard against invalid abbreviation
        try:
            abbreviations = make_abbreviations(raw_abb)
        except ValueError as err:
            raise ValueError(f"Invalid abbreviation: {item}") from err

        if not abbreviations:
            LOGGER.debug("No abbreviations: %s", item)
            skipped.append((item, "No Abbreviations"))
            continue

        glyph_ucodes = str_to_codepoints(char)
        if parsed_ucodes != glyph_ucodes:
            raise ValueError(
                f"{item}: Mismatch between ucode and glyph: "
                f"{parsed_ucodes} != {glyph_ucodes}"
            )

        sample = UnicodeSample(
            ucode=parsed_ucodes,
            glyph=char,
            abbreviations=abbreviations,
            description=description,
        )
        samples.append(sample)

    # check skipped items
    for item, reason in skipped:
        LOGGER.info("❌️ Skipped: %s, reason=%r", item, reason)
    if skipped:
        LOGGER.info("❌️ %d skipped items.", len(skipped))
    else:
        LOGGER.info("✅️ No items skipped.")

    LOGGER.info("✅️ %d items sucessfully pre-processed.", len(samples))
    return samples


def create_autokey_phrase(
    sample: UnicodeSample,
    *,
    path: Path,
    template: JSON,
    sendmode: str,
    overwrite: bool = False,
    duplicates: Literal["error", "skip"] = "error",
) -> PhraseCreationResult:
    """Write a validated sample's AutoKey phrase and metadata files."""
    name = sample.name
    payload_path = path / f"{name}.txt"
    metadata_path = path / f"{name}.json"

    if not overwrite and (payload_path.exists() or metadata_path.exists()):
        if duplicates == "skip":
            return PhraseCreationResult(status="skipped_duplicate", name=name)
        if payload_path.exists():
            raise FileExistsError(f"File {payload_path} already exists.")
        raise FileExistsError(f"File {metadata_path} already exists.")

    payload_path.write_text(sample.glyph, encoding="utf8")
    with metadata_path.open("w", encoding="utf8") as file:
        json.dump(
            template
            | {
                "sendMode": sendmode,
                "abbreviation": template["abbreviation"]
                | {"abbreviations": sample.abbreviations},
                "description": sample.description,
            },
            file,
            indent=True,
        )

    return PhraseCreationResult(status="created", name=name)


def generate_codes(
    directory: str | Path,
    *,
    target_dir: Path,
    template: JSON,
    sendmode: str,
    duplicates: Literal["error", "skip"],
) -> list[UnicodeSample]:
    """Generate an icon collection in a fresh subdirectory of target_dir."""
    folder = Path(directory)
    if not folder.exists():
        raise FileNotFoundError(f"{folder} does not exist.")
    if not folder.is_dir():
        raise NotADirectoryError(f"{folder} is not a directory.")

    target_dir = target_dir / folder.name
    target_dir.mkdir(parents=True)

    LOGGER.info("=" * 80)
    LOGGER.info("Building icons from %s in %s", folder, target_dir)

    parsed: Counter[Glyph] = Counter()  # ucode -> count
    all_abbreviations: dict[Abbreviation, list[Glyph]] = defaultdict(list)
    skipped_duplicates: list[UnicodeSample] = []

    # iterate over all .tsv files in the directory
    for filename in sorted(folder.glob("*.tsv")):
        # load  and process samples
        LOGGER.info("-" * 80)
        raw_icons: list[UnprocessedSample] = load_icons(filename)
        samples: list[UnicodeSample] = process_icons(raw_icons)

        for sample in samples:
            result = create_autokey_phrase(
                sample,
                path=target_dir,
                template=template,
                sendmode=sendmode,
                duplicates=duplicates,
            )

            if result.status == "skipped_duplicate":
                skipped_duplicates.append(sample)
                LOGGER.info(
                    "Skipped duplicate character: %s (%s)", sample.glyph, result.name
                )
                continue

            LOGGER.debug("Registered %s", sample)
            parsed[sample.glyph] += 1
            for abb in sample.abbreviations:
                all_abbreviations[abb].append(sample.glyph)

        LOGGER.info("Finished  %s in %s", filename, target_dir)

    LOGGER.info("=" * 80)
    # duplicates information
    if skipped_duplicates:
        LOGGER.info("Skipped %d duplicate characters:", len(skipped_duplicates))
        for sample in skipped_duplicates:
            LOGGER.info(
                "- %s (%s): %s",
                sample.glyph,
                ", ".join(sample.ucode),
                sample.description,
            )
    else:
        LOGGER.info("✅️ No duplicate characters skipped.")

    num_duplicate_glyphs = 0
    for glyph, count in parsed.items():
        if count > 1:
            LOGGER.info("❌️ Duplicate glyph: %s", glyph)
            num_duplicate_glyphs += 1
    if num_duplicate_glyphs:
        LOGGER.info("❌️ %d duplicate glyphs.", num_duplicate_glyphs)
    else:
        LOGGER.info("✅️ No duplicates detected.")

    # check if all abbreviations are unique
    num_duplicate_abbrv = 0
    for abb, ucodes in all_abbreviations.items():
        if len(ucodes) > 1:
            LOGGER.info("❌️ Duplicate abbreviation: %s -> %s", abb, ucodes)
            num_duplicate_abbrv += 1
    if num_duplicate_abbrv:
        LOGGER.info("❌️ %d duplicate abbreviations.", num_duplicate_abbrv)
    else:
        LOGGER.info("✅️ All abbreviations unique.")

    LOGGER.info("✅️ %d unique glyphs registered.", len(parsed))
    return skipped_duplicates


def install_icons(
    directories: Sequence[str | Path],
    *,
    target_dir: Path,
    sendmode: str,
    duplicates: Literal["error", "skip"],
    build_only: bool = False,
) -> None:
    """Build collections in the repository's build directory, then install them."""
    folders = [Path(directory).resolve() for directory in directories]
    build_dir = BUILD_DIR
    target_dir = target_dir.resolve()

    if build_dir.is_symlink():
        raise ValueError(f"Build directory {build_dir} must not be a symbolic link.")
    if build_dir.exists() and not build_dir.is_dir():
        raise NotADirectoryError(f"{build_dir} is not a directory.")

    if len({folder.name for folder in folders}) != len(folders):
        raise ValueError("Source directories must have distinct folder names.")

    if not build_only:
        if not target_dir.exists():
            raise FileNotFoundError(f"{target_dir} does not exist.")
        if not target_dir.is_dir():
            raise NotADirectoryError(f"{target_dir} is not a directory.")

    # Rebuilding must never remove source files or installed collections.
    protected = folders + [target_dir / folder.name for folder in folders]
    for folder in folders:
        output = build_dir / folder.name
        if output.is_symlink():
            raise ValueError(f"Build directory {output} must not be a symbolic link.")
        output = output.resolve()
        for path in protected:
            path = path.resolve()
            if output.is_relative_to(path) or path.is_relative_to(output):
                raise ValueError(f"Build directory {output} overlaps {path}.")

    source = Path(__file__).resolve().parent / "assets" / "templates" / "phrase.json"
    with source.open(encoding="utf8") as file:
        template: JSON = json.load(file)

    build_dir.mkdir(parents=True, exist_ok=True)

    for folder in folders:
        output = build_dir / folder.name
        if output.exists():
            shutil.rmtree(output)
        generate_codes(
            folder,
            target_dir=build_dir,
            template=template,
            sendmode=sendmode,
            duplicates=duplicates,
        )

    if build_only:
        LOGGER.info("Build complete in %s; installation skipped.", build_dir)
        return

    # Resolve all overwrite choices before changing any installed collection.
    for folder in folders:
        destination = target_dir / folder.name
        if destination.exists() and not query_choice(
            question=f"Directory {destination} already exists. Overwrite?",
            choices=[False, True],
        ):
            LOGGER.debug("Aborting.")
            sys.exit(0)

    for folder in folders:
        destination = target_dir / folder.name
        with tempfile.TemporaryDirectory(
            prefix=".autokey-install-", dir=target_dir
        ) as temporary:
            staged = Path(temporary) / "new"
            backup = Path(temporary) / "old"
            shutil.copytree(build_dir / folder.name, staged)
            if destination.exists():
                destination.rename(backup)
            try:
                staged.rename(destination)
            except OSError:
                if backup.exists():
                    backup.rename(destination)
                raise
        LOGGER.info("Installed icons in %s.", destination)


def _build_phrases(
    source_dir: Path,
    target_dir: Path,
    *,
    sendmode: str,
    codepoint_names: bool = False,
) -> list[Path]:
    """Build TOML phrase assets and return their text files in source order."""
    target_dir = target_dir / source_dir.name
    build_dir = BUILD_DIR / source_dir.name

    for path in (BUILD_DIR, build_dir):
        if path.is_symlink():
            raise ValueError(f"Build directory {path} must not be a symbolic link.")
        if path.exists() and not path.is_dir():
            raise NotADirectoryError(f"{path} is not a directory.")
    for path in (source_dir, target_dir):
        output = build_dir.resolve()
        path = path.resolve()
        if output.is_relative_to(path) or path.is_relative_to(output):
            raise ValueError(f"Build directory {output} overlaps {path}.")

    template_file = source_dir.parent / "templates" / "phrase.json"
    with template_file.open(encoding="utf8") as file:
        template: JSON = json.load(file)

    phrases: list[tuple[Path, str, JSON]] = []
    for source in sorted(source_dir.rglob("*.toml")):
        with source.open("rb") as file:
            config = tomllib.load(file)
        if (
            config.keys() != {"abbreviations", "payload"}
            or not isinstance(config["payload"], str)
            or not isinstance(config["abbreviations"], list)
            or not all(isinstance(value, str) for value in config["abbreviations"])
        ):
            raise ValueError(
                f"Invalid snippet {source}: expected payload (string) "
                "and abbreviations (list of strings)."
            )
        relative_path = source.relative_to(source_dir)
        if codepoint_names:
            name = "_".join(str_to_codepoints(Glyph(config["payload"])))
            relative_path = relative_path.with_stem(name)
        phrases.append((relative_path, source.stem, config))

    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True)

    LOGGER.info("=" * 80)
    LOGGER.info("Building phrases in %s.", build_dir)
    files: list[Path] = []
    for relative_path, description, config in phrases:
        target = build_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        text_file = target.with_suffix(".txt")
        text_file.write_text(config["payload"], encoding="utf8", newline="")
        with target.with_suffix(".json").open("w", encoding="utf8") as file:
            json.dump(
                template
                | {
                    "abbreviation": template["abbreviation"]
                    | {"abbreviations": config["abbreviations"]},
                    "description": description,
                    "sendMode": sendmode,
                },
                file,
                indent=True,
            )
        files.append(text_file)
    return files


def install_special_chars(
    target_dir: Path, /, *, sendmode: str, build_only: bool = False
) -> None:
    """Build bundled special characters, then install the selected phrases."""
    source_dir = Path(__file__).resolve().parent / "assets" / "special_chars"
    files = _build_phrases(
        source_dir, target_dir, sendmode=sendmode, codepoint_names=True
    )
    if build_only:
        LOGGER.info("Special characters built; installation skipped.")
        return
    target_dir = target_dir / source_dir.name
    target_dir.mkdir(parents=True, exist_ok=True)

    for source in files:
        payload = source.read_bytes().decode("utf8")
        codepoints = str_to_codepoints(payload)
        text_file = target_dir / source.name
        json_file = text_file.with_suffix(".json")
        if text_file.exists() or json_file.exists():
            match query_choice(
                f"Found existing special character {payload!r} ({codepoints}).",
                choices=["keep", "overwrite", "delete"],
            ):
                case "keep":
                    continue
                case "overwrite":
                    pass
                case "delete":
                    text_file.unlink(missing_ok=True)
                    json_file.unlink(missing_ok=True)
                    continue
                case _:
                    raise ValueError("Invalid choice.")
        elif not query_choice(
            f"Install special character {payload!r}?",
            choices=[False, True],
        ):
            continue

        shutil.copy2(source, text_file)
        shutil.copy2(source.with_suffix(".json"), json_file)
        LOGGER.info("✅️ Added %s.", payload)


def install_custom_scripts(target_dir: Path, /) -> None:
    """Copy bundled scripts and configs into target_dir/custom_scripts."""
    source_dir = Path(__file__).resolve().parent / "assets" / "custom_scripts"
    target_dir = target_dir / "custom_scripts"

    LOGGER.info("=" * 80)
    LOGGER.info("Installing custom scripts in %s.", target_dir)
    shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
    LOGGER.info(r"Type '\help'+[SPACE] for list of all abbreviations.")


def install_latex_snippets(
    target_dir: Path, /, *, sendmode: str, build_only: bool = False
) -> None:
    """Build bundled TOML snippets, then copy them into target_dir/latex_snippets."""
    source_dir = Path(__file__).resolve().parent / "assets" / "latex_snippets"
    _build_phrases(source_dir, target_dir, sendmode=sendmode)
    build_dir = BUILD_DIR / source_dir.name
    target_dir = target_dir / source_dir.name

    if build_only:
        LOGGER.info("Build complete in %s; installation skipped.", build_dir)
        return

    shutil.copytree(build_dir, target_dir, dirs_exist_ok=True)
    LOGGER.info("Installed LaTeX snippets in %s.", target_dir)


def main() -> None:
    r"""Install function."""
    logging.basicConfig(level=logging.INFO)

    detected_directory = Path.home() / ".config/autokey/data/"
    AUTOKEY_DIR = detected_directory if detected_directory.exists() else Path.cwd()

    parser = argparse.ArgumentParser(
        description="Install icons for usage with autokey.",
    )
    parser.add_argument(
        "--sendmode",
        choices=SEND_MODES,
        default=None,
        type=int,
        help=f"How should character substitutions be performed?\n{SEND_MODES}",
    )
    parser.add_argument(
        "--target-directory",
        default="",
        type=str,
        help="Where to install the icons.",
    )
    parser.add_argument(
        "--autokey-directory",
        default=AUTOKEY_DIR,
        type=Path,
        help="The data directory of AutoKey.",
    )
    parser.add_argument(
        "--build-only",
        "--dry-run",
        action="store_true",
        help="Build icons, LaTeX snippets and special characters without installing them.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Increase verbosity.",
    )
    parser.add_argument(
        "--duplicates",
        "-d",
        choices=["error", "skip"],
        default="skip",
        type=str,
        help="How to handle duplicate generated phrase files.",
    )
    parser.add_argument(
        "source_directories",
        nargs="*",
        default=["icons/julia_unicode/", "icons/custom_unicode/"],
        type=str,
        help="Directories holding the `.tsv` files to be installed.",
    )
    args = parser.parse_args()

    if args.verbose:
        LOGGER.setLevel(logging.DEBUG)

    if not args.build_only:
        check_autokey_version()
        if not detected_directory.exists():
            LOGGER.warning(
                "Autokey directory not found. Installing into %s.",
                args.autokey_directory / args.target_directory,
            )

    # if sendmode is missing, ask user
    if args.sendmode is None:
        sendmode = query_choice(
            question="How should character substitutions be performed?",
            choices=SEND_MODES,
        )
    else:
        sendmode = SEND_MODES[args.sendmode]

    target_dir = args.autokey_directory / args.target_directory

    install_icons(
        args.source_directories,
        target_dir=target_dir,
        sendmode=sendmode,
        duplicates=args.duplicates,
        build_only=args.build_only,
    )
    install_latex_snippets(target_dir, sendmode=sendmode, build_only=args.build_only)
    install_special_chars(target_dir, sendmode=sendmode, build_only=args.build_only)

    if args.build_only:
        return

    install_custom_scripts(target_dir)
    LOGGER.debug(r"Finished Installation. Restart AutoKey to enable!")


if __name__ == "__main__":
    main()

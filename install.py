#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# ///
"""Generate phrases for autokey."""

# %% Imports

import argparse
import csv
import json
import logging
import re
import shutil
import sys
from collections import Counter, defaultdict
from collections.abc import Generator, Sequence
from pathlib import Path
from typing import Any, Final, NamedTuple, Self, TypeIs

# In[2]:
# Globals / Constants / Templates
LOGGER = logging.getLogger(__name__)
type JSON = dict[str, Any]
# any printable ascii character except backslash (x5C) and space (x20)
LEGAL_CHARS = re.compile(r"[\x21-\x5B\x5D-\x7E]+")
"""Regex pattern for legal characters."""
SPECIAL_DIR = "custom_special"
"""Directory for special characters."""
ILLEGAL_FILENAME_CHARS_LINUX = r"""/"""
ILLEGAL_FILENAME_CHARS_WINDOWS = r"""\/?%*:|"<>.,;="""


class Glyph(str):
    """Character type."""

    def __new__(cls, value: str) -> Self:
        if not is_glyph(value):
            raise ValueError(f"{value!r} is not a valid character.")
        return super().__new__(cls, value)


def is_glyph(s: object, /) -> TypeIs[Glyph]:
    """Check whether string is a single character."""
    # test exact match against regex
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


def is_codepoint(s: object, /) -> TypeIs[CodePoint]:
    """Check whether string is a unicode-code (like U+0000A)."""
    # test exact match against regex
    return isinstance(s, str) and CodePoint.PATTERN.fullmatch(s) is not None


def parse_codepoints(s: str, /) -> list[CodePoint]:
    """Parse a string of the form 'U+0000A + U+0000B' into a list of CodePoints."""
    codepoints = [CodePoint(code.strip()) for code in s.split(" + ")]
    # simplify code points by stripping leading zeros
    return [CodePoint(f"U+{int(code[2:], 16):04X}") for code in codepoints]


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


def is_abbreviation(s: object, /) -> TypeIs[Abbreviation]:
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


# %% Helper scripts
TEMPLATE: JSON = {
    "abbreviation": {
        "abbreviations": [],
        "backspace": True,
        "ignoreCase": False,
        "immediate": True,
        "triggerInside": True,
        "wordChars": "[^\\t]",
    },
    "description": "",
    "filter": {
        "regex": None,
        "isRecursive": False,
    },
    "hotkey": {
        "modifiers": [],
        "hotKey": None,
    },
    "modes": [1],
    "matchCase": False,
    "omitTrigger": False,
    "prompt": False,
    "sendMode": r"<shift>+<insert>",
    "showInTrayMenu": False,
    "type": "phrase",
    "usageCount": 0,
}


# %% Helper function send-mode

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
        else:
            try:
                if user_choice == "" and default is not None:
                    return options[default]
                return options[int(user_choice)]
            except (KeyError, ValueError):
                print("Did not understand input.")
            continue


def get_sendmode() -> str:
    """Ask the user which sendmode to use."""
    sendmode = query_choice(
        question="How should character substitutions be performed?",
        choices=SEND_MODES,
    )
    return sendmode


# %% Generate phrases
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

    def __repr__(self) -> str:
        char, ucode, abbrevations = self.glyph, self.ucode, self.abbreviations
        return f"{ucode}: {char!r}  {abbrevations=!s}"


TABULATOR: UnicodeSample = UnicodeSample(
    ucode=[CodePoint("U+0009")],
    glyph=Glyph("\t"),
    abbreviations=[Abbreviation(r"\t ")],
    description="Tabulator",
)

NEWLINE: UnicodeSample = UnicodeSample(
    ucode=[CodePoint("U+000A")],
    glyph=Glyph("\n"),
    abbreviations=[Abbreviation(r"\n ")],
    description="Newline",
)

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
    r"""Process the unicode samples."""
    samples: list[UnicodeSample] = []
    # parsed = Counter()  # ucode -> count
    # all_abbreviations = defaultdict(list)  # abbrv -> ucode
    LOGGER.info("Pre-Processing %d items.", len(data))
    skipped: list[tuple[UnprocessedSample, str]] = []  # items

    for item in data:
        ucode, char, raw_abb, description = item
        parsed_ucodes = parse_codepoints(ucode)

        # guard against invalid character
        if not is_glyph(char):
            LOGGER.debug("Invalid character: %s=%s", item)
            skipped.append((
                item,
                f"Invalid character {char!r}={as_hex(char)}",
            ))
            continue

        # guard against invalid unicode
        if not all(is_codepoint(code) for code in parsed_ucodes):
            LOGGER.debug("Invalid unicode: %s", item)
            skipped.append((item, "Invalid Unicode"))
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
    template: JSON = TEMPLATE,
    overwrite: bool = False,
) -> None:
    """Create the autokey phrase and metadata file."""
    metadata = template | {
        "abbreviation": template["abbreviation"]
        | {"abbreviations": sample.abbreviations},
        "description": sample.description,
    }

    if sample.ucode != str_to_codepoints(sample.glyph):
        raise ValueError(
            f"{sample}: Mismatch between ucode and glyph"
            f"{sample.ucode} != {str_to_codepoints(sample.glyph)}"
        )

    name = "_".join(sample.ucode)

    if (payload_path := path / f"{name}.txt").exists() and not overwrite:
        raise FileExistsError(f"File {payload_path} already exists.")
    if (metadata_path := path / f".{name}.json").exists() and not overwrite:
        raise FileExistsError(f"File {metadata_path} already exists.")

    with (
        open(payload_path, "w", encoding="utf8") as file,
        open(metadata_path, "w", encoding="utf8") as metadata_file,
    ):
        file.write(sample.glyph)
        json.dump(metadata, metadata_file, indent=True)


def generate_codes(directory: str | Path, *, target_dir: Path, template: JSON) -> None:
    """Read the icons from filename and create phrases files in target_dir."""
    folder = Path(directory)
    if not folder.exists():
        raise FileNotFoundError(f"{folder} does not exist.")
    if not folder.is_dir():
        raise NotADirectoryError(f"{folder} is not a directory.")

    # region make the target directory -----------------------------------------
    # append the fodler name to the target directory
    target_dir = target_dir / folder.name

    if target_dir.exists():
        # ask user if they want to overwrite
        overwrite = query_choice(
            question=f"Directory {target_dir} already exists. Overwrite?",
            choices=[False, True],
        )
        if not overwrite:
            LOGGER.debug("Aborting.")
            sys.exit(0)

        # delete directory
        shutil.rmtree(target_dir)

    # ensure directory exists
    target_dir.mkdir(exist_ok=True)
    # endregion ----------------------------------------------------------------

    LOGGER.info("=" * 80)
    LOGGER.info("Installing icons from %s", folder)

    parsed: Counter[Glyph] = Counter()  # ucode -> count
    all_abbreviations: dict[Abbreviation, list[Glyph]] = defaultdict(list)

    # iterate over all .tsv files in the directory
    for filename in folder.glob("*.tsv"):
        # load  and process samples
        LOGGER.info("-" * 80)
        raw_icons: list[UnprocessedSample] = load_icons(filename)
        samples: list[UnicodeSample] = process_icons(raw_icons)

        for sample in samples:
            create_autokey_phrase(
                sample,
                path=target_dir,
                template=template,
            )

            LOGGER.debug("Registered %s", sample)
            parsed[sample.glyph] += 1
            for abb in sample.abbreviations:
                all_abbreviations[abb].append(sample.glyph)

        LOGGER.info("Finished  %s in %s", filename, target_dir)

    LOGGER.info("=" * 80)
    # duplicates information
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


# %% Generate help script

HELP_SCRIPT = r"""#!/usr/bin/env python
import webbrowser
webbrowser.open("https://docs.julialang.org/en/v1/manual/unicode-input/")
"""

HELP_CONFIG: JSON = {
    "type": "script",
    "description": "Help for Julia Unicode",
    "store": {},
    "modes": [1],
    "usageCount": 0,
    "prompt": False,
    "omitTrigger": False,
    "showInTrayMenu": True,
    "abbreviation": {
        "abbreviations": [
            r"\\help ",
        ],
        "backspace": False,
        "ignoreCase": False,
        "immediate": True,
        "triggerInside": True,
        "wordChars": "[\\w]",
    },
    "hotkey": {
        "modifiers": [],
        "hotKey": None,
    },
    "filter": {
        "regex": None,
        "isRecursive": False,
    },
}


def generate_character(
    sample: UnicodeSample,
    *,
    template: JSON = TEMPLATE,
    target_dir: Path,
    default: bool = False,
) -> None:
    r"""Generate special characters."""
    text_file = target_dir / f"{sample.ucode}.txt"
    json_file = target_dir / f".{sample.ucode}.json"
    if text_file.exists() or json_file.exists():
        match query_choice(
            f"Found existing special character {sample.glyph!r} ({sample.ucode}).",
            choices=["keep", "overwrite", "delete"],
        ):
            case "keep":
                pass
            case "overwrite":
                text_file.unlink()
                json_file.unlink()
            case "delete":
                text_file.unlink()
                json_file.unlink()
                return  # exit early
            case _:
                raise ValueError("Invalid choice.")
    else:
        match query_choice(
            f"Install special character {sample.glyph!r}?",
            choices=[False, True],
        ):
            case False:
                return
            case True:
                pass
            case _:
                raise ValueError("Invalid choice.")

    target_dir.mkdir(exist_ok=True)
    create_autokey_phrase(sample, template=template, path=target_dir, overwrite=True)
    LOGGER.info("✅️ Added %s.", sample.glyph)


def generate_help(*, target_dir: Path) -> None:
    r"""Create help script and config."""
    LOGGER.info("=" * 80)
    LOGGER.info("Creating help script in %s.", target_dir)

    target_dir.mkdir(exist_ok=True)

    with open(target_dir / "julia_unicode_help.py", "w", encoding="utf8") as file:
        file.write(HELP_SCRIPT)

    with open(target_dir / "julia_unicode_help.json", "w", encoding="utf8") as file:
        json.dump(HELP_CONFIG, file, indent=True)

    LOGGER.info(r"Type '\help'+[SPACE] for list of all abbreviations.")


# %% Unused


def make_template(abbreviations: list[str], description: str, sendmode: str) -> JSON:
    r"""Create the template."""
    return TEMPLATE | {
        "abbreviation": Abbreviation | {"abbreviations": abbreviations},
        "description": description,
        "sendMode": sendmode,
    }


# %% Main


def main() -> None:
    r"""Install function."""
    logging.basicConfig(level=logging.INFO)

    detected_directory = Path.home() / ".config/autokey/data/"
    AUTOKEY_DIR = detected_directory if detected_directory.exists() else Path.cwd()

    if detected_directory.exists():
        LOGGER.debug("Found autokey directory at %s.", detected_directory)
    else:
        LOGGER.warning(
            "Autokey directory not found. Will generate files locally instead."
        )

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
        type=str,
        help="The data directory of AutoKey.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Increase verbosity.",
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

    # if sendmode is missing, ask user
    sendmode = get_sendmode() if args.sendmode is None else SEND_MODES[args.sendmode]

    # validate target_directory
    target_dir = AUTOKEY_DIR / args.target_directory

    if not target_dir.exists():
        raise FileNotFoundError(f"{target_dir} does not exist.")
    if not target_dir.is_dir():
        raise NotADirectoryError(f"{target_dir} is not a directory.")

    template = TEMPLATE | {"sendMode": sendmode}

    for directory in args.source_directories:
        generate_codes(directory, target_dir=target_dir, template=template)

    # add special characters
    special = target_dir / SPECIAL_DIR
    generate_character(TABULATOR, target_dir=special, template=template, default=False)
    generate_character(NEWLINE, target_dir=special, template=template, default=False)

    generate_help(target_dir=target_dir / "help")
    LOGGER.debug(r"Finished Installation. Restart AutoKey to enable!")


if __name__ == "__main__":
    main()

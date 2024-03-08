#!/usr/bin/env python3
"""Generate phrases for autokey."""

# %% Imports

import argparse
import re
import csv
import json
import logging
import sys
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Final, NewType, TypeGuard, NamedTuple, Any, TypeVar, TypeAlias

# In[2]:
# Globals / Constants / Templates
CHAR = NewType("CHAR", str)
"""Character type."""
UCODE = NewType("UCODE", str)
"""Unicode code type."""
ABBREVIATION = NewType("ABBREVIATION", str)
"""Abbreviation type."""
LOGGER = logging.getLogger(__name__)

T = TypeVar("T")
"""Generic type for choices."""
JSON: TypeAlias = dict[str, Any]
# %% Helper scripts

UNICODE_PATTERN = re.compile(r"U\+[0-9A-F]{4,6}")
"""Regex pattern for unicode codes."""
# any printable ascii character except backslash (x5C) and space (x20)
LEGAL_CHARS = re.compile(r"[\x21-\x5B\x5D-\x7E]+")
"""Regex pattern for legal characters."""
ABBREVIATION_PATTERN = re.compile(r"\x5C[\x21-\x7E]+\x20")
# ABBREVIATION_PATTERN = re.compile(r"\x5C[\x21-\x5B\x5D-\x7E]+\x20")  # exclude x5C (backslash)
"""Regex pattern for abbreviations start with backslash (5C) and end in space (20)."""


def is_char(s: object, /) -> TypeGuard[CHAR]:
    """Check whether string is a single character."""
    # test exact match against regex
    return isinstance(s, str) and len(s) == 1


def is_unicode(s: object, /) -> TypeGuard[UCODE]:
    """Check whether string is a unicode-code (like U+0000A)."""
    # test exact match against regex
    return isinstance(s, str) and UNICODE_PATTERN.fullmatch(s) is not None


def is_abbreviation(s: object, /) -> TypeGuard[ABBREVIATION]:
    """Check if string is a valid abbreviation.

    Abbreviations must begin with a backslash followed by one or more
    legal characters and terminate with a single space.
    """
    return isinstance(s, str) and ABBREVIATION_PATTERN.fullmatch(s) is not None


def as_char(s: str, /) -> CHAR:
    """Convert string to character."""
    if not is_char(s):
        raise ValueError(f"{s!r} is not a valid character.")
    return s


def as_ucode(s: str, /) -> UCODE:
    """Convert string to unicode code."""
    if not is_unicode(s):
        raise ValueError(f"{s!r} is not a valid unicode code.")
    return s


def as_abbreviation(s: str, /) -> ABBREVIATION:
    """Convert string to abbreviation."""
    if not is_abbreviation(s):
        raise ValueError(
            f"{s!r} is not a valid abbreviation."
            "\nAbbrevations must begin with a backslash and terminate with a space."
            "\nInside the abbrevations only the printable ascii characters x21-x7e are allowed,"
            " except backslash x5C."
        )
    return s


def make_abbreviations(raw_data: str, /) -> list[ABBREVIATION]:
    """Create the abbreviation list from the raw data."""
    abbreviations: list[ABBREVIATION] = []

    if not raw_data:
        return abbreviations

    for raw_abb in raw_data.split(", "):
        abb = as_abbreviation(raw_abb + " ")  # add single trailing space
        abbreviations.append(abb)

    return abbreviations


ILLEGAL_FILENAME_CHARS_LINUX = r"""/"""
ILLEGAL_FILENAME_CHARS_WINDOWS = r"""\/?%*:|"<>.,;="""

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

SEND_MODES: Final[list[str]] = [
    r"<ctrl>+v",
    r"<ctrl>+<shift>+v",
    r"<shift>+<insert>",
]
DEFAULT_QUESTION = "Please pick one of the following:"


def query_choice(
    *,
    choices: list[T],
    question: str = DEFAULT_QUESTION,
    default: int | None = 0,
) -> T:
    """Ask the user to pick an option."""
    options = dict(enumerate(choices))

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


HEADER = (
    "Code point(s)",
    "Character(s)",
    "Tab completion sequence(s)",
    "Unicode name(s)",
)
"""Header for the unicode samples."""


class UnprocessedSample(NamedTuple):
    """Named tuple for unprocessed unicode samples."""

    ucode: str
    char: str
    abbreviations: str
    description: str

    def __repr__(self) -> str:
        char, ucode, abbrevations = self.char, self.ucode, self.abbreviations
        return f"{char=!r}: {ucode=!r} {abbrevations=!r}"


class UnicodeSample(NamedTuple):
    """Named tuple for unicode samples."""

    ucode: UCODE
    char: CHAR
    abbreviations: list[ABBREVIATION]
    description: str


def load_icons(fname: str | Path, /) -> list[UnprocessedSample]:
    """Load the icons from the tsv file."""
    LOGGER.info("Parsing %s", fname)

    with open(fname, "r", encoding="utf8") as tsv_file:
        # scraped from https://docs.julialang.org/en/v1/manual/unicode-input/
        reader_obj = csv.reader(tsv_file, delimiter="\t")
        items: list[list[str]] = list(reader_obj)

    header = items[0]
    data = items[1:]

    if missing_cols := set(HEADER) - set(header):  # pyright: ignore[reportOperatorIssue]
        raise ValueError(f"Missing columns: {missing_cols}")

    mask = [idx for idx, col in enumerate(header) if col in HEADER]

    if mask == [0, 1, 2, 3]:
        return [UnprocessedSample(*row[:4]) for row in data]
    return [UnprocessedSample(*(row[i] for i in mask)) for row in data]


def process_icons(data: list[UnprocessedSample], /) -> list[UnicodeSample]:
    samples: list[UnicodeSample] = []
    # parsed = Counter()  # ucode -> count
    # all_abbreviations = defaultdict(list)  # abbrv -> ucode
    LOGGER.info("Pre-Processing %d items.", len(data))
    skipped: list[tuple[UnprocessedSample, str]] = []  # items

    for item in data:
        ucode, char, raw_abb, description = item

        # guard against invalid character
        if not is_char(char):
            LOGGER.debug("Invalid character: %s", item)
            skipped.append((item, "Invalid Character"))
            continue

        # guard against invalid unicode
        if not is_unicode(ucode):
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
            ucode=ucode,
            char=char,
            abbreviations=abbreviations,
            description=description,
        )
        samples.append(sample)

    # check skipped items
    for item, reason in skipped:
        LOGGER.info("❌ Skipped: %s, reason=%r", item, reason)
    if skipped:
        LOGGER.info("❌ %d skipped items.", len(skipped))
    else:
        LOGGER.info("✅ No items skipped.")

    LOGGER.info("✅ %d items sucessfully pre-processed.", len(samples))
    return samples


def create_autokey_phrase(
    sample: UnicodeSample,
    *,
    path: Path,
    template: JSON,
) -> None:
    """Create the autokey phrase and metadata file."""
    metadata = template | {
        "abbreviation": template["abbreviation"]
        | {"abbreviations": sample.abbreviations},
        "description": sample.description,
    }

    if (payload_path := path / f"{sample.ucode}.txt").exists():
        raise FileExistsError(f"File {payload_path} already exists.")
    if (metadata_path := path / f".{sample.ucode}.json").exists():
        raise FileExistsError(f"File {metadata_path} already exists.")

    with (
        open(payload_path, "w", encoding="utf8") as file,
        open(metadata_path, "w", encoding="utf8") as metadata_file,
    ):
        file.write(sample.char)
        json.dump(metadata, metadata_file, indent=True)


def generate_codes(directory: str | Path, *, target_dir: Path, template: JSON) -> None:
    """Read the icons from filename and create phrases files in target_dir."""
    folder = Path(directory)
    assert folder.exists(), f"{folder} does not exist."
    assert folder.is_dir(), f"{folder} is not a directory."

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

    parsed: Counter[UCODE] = Counter()  # ucode -> count
    all_abbreviations: dict[ABBREVIATION, list[UCODE]] = defaultdict(list)

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
            parsed[sample.ucode] += 1
            for abb in sample.abbreviations:
                all_abbreviations[abb].append(sample.ucode)

        LOGGER.info("Finished  %s in %s", filename, target_dir)

    LOGGER.info("=" * 80)
    # duplicates information
    num_duplicate_ucodes = 0
    for ucode, count in parsed.items():
        if count > 1:
            LOGGER.info("❌ Duplicate unicode: %s", ucode)
            num_duplicate_ucodes += 1
    if num_duplicate_ucodes:
        LOGGER.info("❌ %d duplicate unicodes.", len(parsed))
    else:
        LOGGER.info("✅ No duplicates detected.")

    # check if all abbreviations are unique
    num_duplicate_abbrv = 0
    for abb, ucodes in all_abbreviations.items():
        if len(ucodes) > 1:
            LOGGER.info("❌ Duplicate abbreviation: %s -> %s", abb, ucodes)
            num_duplicate_abbrv += 1
    if num_duplicate_abbrv:
        LOGGER.info("❌ %d duplicate abbreviations.", num_duplicate_abbrv)
    else:
        LOGGER.info("✅ All abbreviations unique.")

    LOGGER.info("✅ %d unique characters registered.", len(parsed))


# %% Generate help script

HELP_SCRIPT = r"""
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
            r"\help ",
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


def generate_help(*, target_dir: Path) -> None:
    """Create help script and config."""
    LOGGER.info("=" * 80)
    LOGGER.info("Creating help script in %s.", target_dir)

    with open(target_dir / "julia_unicode_help.py", "w", encoding="utf8") as file:
        file.write(HELP_SCRIPT)

    with open(target_dir / "julia_unicode_help.json", "w", encoding="utf8") as file:
        json.dump(HELP_CONFIG, file, indent=True)

    LOGGER.info(r"Type '\help'+[SPACE] for list of all abbreviations.")


# %% Unused


def make_template(abbreviations: list[str], description: str, sendmode: str) -> JSON:
    """Create the template."""
    return TEMPLATE | {
        "abbreviation": ABBREVIATION | {"abbreviations": abbreviations},
        "description": description,
        "sendMode": sendmode,
    }


# %% Main


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    AUTOKEY_DIR = Path.home() / ".config/autokey/"
    if AUTOKEY_DIR.exists():
        LOGGER.debug("Found autokey directory at %s.", AUTOKEY_DIR)
    else:
        LOGGER.warning(
            "Autokey directory not found. Will generate files locally instead."
        )
    BASE_PATH = AUTOKEY_DIR / "data/" if AUTOKEY_DIR.exists() else Path.cwd()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sendmode",
        choices=SEND_MODES,
        default=None,
        help="How should character substitutions be performed?",
    )
    parser.add_argument(
        "--target-directory",
        default=BASE_PATH,
        type=Path,
        help="Where to install the icons.",
    )
    parser.add_argument(
        "directories",
        nargs="*",
        default=["icons/julia_unicode/", "icons/custom_unicode/"],
        type=str,
        help="Directories holding the `.tsv` files to be installed.",
    )
    args = parser.parse_args()

    # if sendmode is missing, ask user
    sendmode = get_sendmode() if args.sendmode is None else args.sendmode

    # validate target_directory
    target_dir = Path(args.target_directory)
    assert target_dir.exists(), f"{target_dir} does not exist."
    assert target_dir.is_dir(), f"{target_dir} is not a directory."

    template = TEMPLATE | {"sendMode": sendmode}

    for directory in args.directories:
        generate_codes(directory, target_dir=target_dir, template=template)

    generate_help(target_dir=target_dir)
    LOGGER.debug(r"Finished Installation. Restart AutoKey to enable!")


if __name__ == "__main__":
    main()

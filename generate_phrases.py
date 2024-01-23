#!/usr/bin/env python3
"""Generate phrases for autokey."""

# %% Imports

import re
import csv
import json
import logging
import sys
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Final, NewType, TypeGuard

# In[2]:
# Globals / Constants / Templates

LOGGER = logging.getLogger(__name__)
BASE_PATH = Path.home() / ".config/autokey/data/"

if not BASE_PATH.exists():
    print(f"{BASE_PATH} does not exist. Will generate files locally instead.")
    BASE_PATH = Path.cwd()
else:
    print(f"Found autokey directory at {BASE_PATH}.")

# %% Helper scripts

UNICODE_PATTERN = re.compile(r"U\+[0-9A-F]{4,6}")
"""Regex pattern for unicode codes."""
# any printable ascii character except backslash (x5C) and space (x20)
LEGAL_CHARS = re.compile(r"[\x21-\x5B\x5D-\x7E]+")
"""Regex pattern for legal characters."""
ABBREVIATION_PATTERN = re.compile(r"\x5C[\x21-\x5B\x5D-\x7E]+\x20")
"""Regex pattern for abbreviations start with backslash (5C) and end in space (20)."""

CHAR = NewType("CHAR", str)
"""Character type."""
UCODE = NewType("UCODE", str)
"""Unicode code type."""
ABBREVIATION = NewType("ABBREVIATION", str)
"""Abbreviation type."""


def is_char(s: str, /) -> TypeGuard[CHAR]:
    """Check whether string is a single character."""
    # test exact match against regex
    return isinstance(s, str) and len(s) == 1


def is_unicode(s: str, /) -> TypeGuard[UCODE]:
    """Check whether string is a unicode-code (like U+0000A)."""
    # test exact match against regex
    return UNICODE_PATTERN.fullmatch(s) is not None


def is_abbreviation(s: str, /) -> TypeGuard[ABBREVIATION]:
    """Check if string is a valid abbreviation.

    Abbreviations must begin with a backslash followed by one or more
    legal characters and terminate with a single space.
    """
    return ABBREVIATION_PATTERN.fullmatch(s) is not None


ILLEGAL_FILENAME_CHARS_LINUX = r"""/"""
ILLEGAL_FILENAME_CHARS_WINDOWS = r"""\/?%*:|"<>.,;="""

TEMPLATE = {
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


def query_choice(*, choices, question=DEFAULT_QUESTION, default=0):
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


def load_icons(fname: str | Path) -> list[list[str]]:
    """Load the icons from the tsv file."""

    with open(fname, "r", encoding="utf8") as tsv_file:
        # scraped from https://docs.julialang.org/en/v1/manual/unicode-input/
        reader_obj = csv.reader(tsv_file, delimiter="\t")
        return list(reader_obj)


def make_abbreviation(raw_data: str, /) -> list[ABBREVIATION]:
    """Create the abbreviation list from the raw data."""
    abbreviations: list[ABBREVIATION] = []

    for raw_abb in raw_data.split(", "):
        abb = raw_abb + " "  # add single trailing space
        if not is_abbreviation(abb):
            raise ValueError(f"{abb!r} is not valid abbreviation.")
        abbreviations.append(abb)

    return abbreviations


def make_template(abbreviations: list[str], description: str, sendmode: str):
    """Create the template."""
    return TEMPLATE | {
        "abbreviation": ABBREVIATION | {"abbreviations": abbreviations},
        "description": description,
        "sendMode": sendmode,
    }


def create_autokey_phrase(
    ucode: UCODE,
    char: CHAR,
    abbreviations: list[ABBREVIATION],
    description: str,
    *,
    path: Path,
    template: dict,
) -> None:
    """Create the autokey phrase and metadata file."""
    metadata = template | {
        "abbreviation": template["abbreviation"] | {"abbreviations": abbreviations},
        "description": description,
    }

    if (payload_path := path / f"{ucode}.txt").exists():
        raise FileExistsError(f"File {payload_path} already exists.")
    if (metadata_path := path / f".{ucode}.json").exists():
        raise FileExistsError(f"File {metadata_path} already exists.")

    with (
        open(payload_path, "w", encoding="utf8") as file,
        open(metadata_path, "w", encoding="utf8") as metadata_file,
    ):
        file.write(char)
        json.dump(metadata, metadata_file, indent=True)


def generate_codes(filename: str, target_dir: str, template: dict) -> None:
    """Read the icons from filename and create phrases files in target_dir."""

    if (path := BASE_PATH / target_dir).exists():
        # ask user if they want to overwrite
        overwrite = query_choice(
            question=f"Directory {path} already exists. Overwrite?",
            choices=[False, True],
        )
        if not overwrite:
            LOGGER.info("Aborting.")
            sys.exit(0)

        # delete directory
        shutil.rmtree(path)

    # ensure directory exists
    path.mkdir(exist_ok=True)

    # load data
    data = load_icons(filename)
    # header = data[0]
    assert len(data[1]) == 4, f"Wrong data format. {data[1]}"

    LOGGER.info("-" * 80)
    LOGGER.info("Installing icons from %s to %s", filename, path)

    parsed = Counter()  # ucode -> count
    all_abbreviations = defaultdict(list)  # abbrv -> ucode
    skipped = []  # items

    for item in data[1:]:
        ucode, char, raw_abb, description = item

        # guard against invalid unicode
        if not is_unicode(ucode):
            LOGGER.error("Invalid unicode: %s", item)
            skipped.append((item, "Invalid unicode"))
            continue

        if not is_char(char):
            LOGGER.error("Invalid character: %s", item)
            skipped.append((item, "Invalid character"))
            continue

        try:
            abbreviations = make_abbreviation(raw_abb)
        except ValueError as err:
            raise ValueError(f"Invalid abbreviation: {item}") from err

        create_autokey_phrase(
            ucode=ucode,
            char=char,
            abbreviations=abbreviations,
            description=description,
            path=path,
            template=template,
        )

        LOGGER.info("Registered %s", item)
        parsed[ucode] += 1
        for abb in abbreviations:
            all_abbreviations[abb].append(ucode)

    LOGGER.info("-" * 80)
    LOGGER.info("Finished  %s in %s", filename, path)

    # duplicates information
    num_duplicate_ucodes = 0
    for ucode, count in parsed.items():
        if count > 1:
            LOGGER.warning("❌ Duplicate unicode: %s", ucode)
            num_duplicate_ucodes += 1
    if num_duplicate_ucodes:
        LOGGER.warning("❌ %d duplicate unicodes.", len(parsed))
    else:
        LOGGER.info("✅ No duplicates detected.")

    # check if all abbreviations are unique
    num_duplicate_abbrv = 0
    for abb, ucodes in all_abbreviations.items():
        if len(ucodes) > 1:
            LOGGER.warning("❌ Duplicate abbreviation: %s -> %s", abb, ucodes)
            num_duplicate_abbrv += 1
    if num_duplicate_abbrv:
        LOGGER.warning("❌ %d duplicate abbreviations.", num_duplicate_abbrv)
    else:
        LOGGER.info("✅ All abbreviations unique.")

    # check skipped items
    for item, reason in skipped:
        LOGGER.warning("❌ Skipped: %s, reason=%s", item, reason)
    if skipped:
        LOGGER.warning("❌ %d skipped items.", len(skipped))
    else:
        LOGGER.info("✅ No items skipped.")

    LOGGER.info("-" * 80)


# %% Generate help script

HELP_SCRIPT = r"""
import webbrowser
webbrowser.open("https://docs.julialang.org/en/v1/manual/unicode-input/")
"""

HELP_CONFIG = {
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


def generate_help() -> None:
    """Create help script and config."""
    with open(BASE_PATH / "julia_unicode_help.py", "w", encoding="utf8") as file:
        file.write(HELP_SCRIPT)

    with open(BASE_PATH / "julia_unicode_help.json", "w", encoding="utf8") as file:
        json.dump(HELP_CONFIG, file, indent=True)

    LOGGER.info("Created help script in %s", BASE_PATH)
    LOGGER.info(r"Type '\help'+[SPACE] for list of all abbreviations.")


# %% Main


def main():
    logging.basicConfig(level=logging.INFO)
    sendmode = get_sendmode()
    template = TEMPLATE | {"sendMode": sendmode}

    # clean up old files
    generate_codes("icons/icons.tsv", "julia_unicode", template=template)
    generate_codes("icons/custom_icons.tsv", "custom_unicode", template=template)

    # add custom unicode icons for all csv files in icons/
    # for fname in Path("icons").glob("*.csv"):
    #     generate_phrases(fname, fname.stem)

    generate_help()
    LOGGER.info(r"Finished Installation. Restart AutoKey to enable.")


if __name__ == "__main__":
    main()

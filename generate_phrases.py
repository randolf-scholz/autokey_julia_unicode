#!/usr/bin/env python3
"""Generate phrases for autokey."""

# In[1]:

import csv
import json
import logging
import sys
import time
from collections import Counter
from pathlib import Path
from string import ascii_letters, digits, hexdigits
from typing import Optional

# In[2]:
# Globals / Constants / Templates

LOGGER = logging.getLogger(__name__)
BASE_PATH = Path.home() / ".config/autokey/data/"


if not BASE_PATH.exists():
    print(f"{BASE_PATH} does not exist. Will generate files locally instead.")
    BASE_PATH = Path.cwd()
else:
    print(f"Found autokey directory at {BASE_PATH}.")

UNICODE_PATTERN = ("U", "+") + (hexdigits,) * 5
ABBRV_CHARS = ascii_letters + digits + ";,.:^/_+-=()!|*~%"

ILLEGAL_FILENAME_CHARS_LINUX = ["/"]
ILLEGAL_FILENAME_CHARS_WINDOWS = list(r'\/?%*:|"<>.,;=')


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


HELPSCRIPT = """
import webbrowser
webbrowser.open("https://docs.julialang.org/en/v1/manual/unicode-input/")
"""

HELPCONFIG = {
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

# In[3]:


def is_unicode(s: str) -> bool:
    """Check wether string is a unicode-code (like U+0000A)."""
    return s[0:2] == "U+" and all(c in hexdigits for c in s[2:])


def is_abbrv(s: str) -> bool:
    """Check if string is a valid abbreviation."""
    return len(s) > 1 and s[0] == "\\" and " " not in s and "\t" not in s
    # all(c in ABBRV_CHARS for c in s[1:])


def query_choice(choices: list[str], question: Optional[str] = None) -> str:
    """Ask the user to pick an option."""
    if question is None:
        question = "Please pick one of the following:"

    options: dict[int, str] = dict(enumerate(choices))

    while True:
        try:
            print(question)
            for i, option in options.items():
                print(f"{i:3d}. {option}")
            user_choice = input("Enter integer: ")
        except KeyboardInterrupt:
            print("Operation aborted. Exiting.")
            sys.exit(0)
        else:
            if user_choice.isdigit() and int(user_choice) in options:
                break
            print("Did not understand input.")
    return options[int(user_choice)]


def set_sendmode() -> None:
    """Ask the user which sendmode to use."""
    sendmode = query_choice(
        question="How should character substitutions be performed?",
        choices=[r"<ctrl>+v", r"<ctrl>+<shift>+v", r"<shift>+<insert>"],
    )

    TEMPLATE["sendMode"] = sendmode


def load_icons(fname: str | Path) -> list[list[str]]:
    """Load the icons from the csv file."""
    with open(fname, "r", encoding="utf8") as csvfile:
        # scraped from https://docs.julialang.org/en/v1/manual/unicode-input/
        reader_obj = csv.reader(csvfile, delimiter="\t")
        data = list(reader_obj)
    return data


def generate_help() -> None:
    """Create help script and config."""
    with open(BASE_PATH / "julia_unicode_help.py", "w", encoding="utf8") as file:
        file.write(HELPSCRIPT)

    with open(BASE_PATH / "julia_unicode_help.json", "w", encoding="utf8") as file:
        json.dump(HELPCONFIG, file, indent=True)

    LOGGER.info("Created help script in %s", BASE_PATH)
    LOGGER.info(r"Type '\help'+[SPACE] for list of all abbreviations.")


def gerenerate_phrases(filename: str, target_dir: str) -> None:
    """Read the icons from filename and create phrases files in target_dir."""
    data = load_icons(filename)
    path = BASE_PATH / target_dir
    path.mkdir(exist_ok=True)

    assert len(data[1]) == 4, f"Wrong data format. {data[1]}"

    parsed = Counter()  # ucode -> count
    skipped = []  # items

    for item in data[1:]:
        ucode, char, abbrv, note = item
        # sometimes multiple abbreviations exist
        abbrvs: list[str] = [abb.strip(" ") for abb in abbrv.split(", ")]

        for abb in abbrvs:
            assert is_abbrv(abb), f"{abb} is not valid abbreviation."

        # add space at the end, otherwise \delta cannot be typed as \del exists
        TEMPLATE["abbreviation"]["abbreviations"] = [abb + " " for abb in abbrvs]
        TEMPLATE["description"] = note

        # guard against invalid unicode
        if not is_unicode(ucode):
            LOGGER.error("Invalid unicode: %s", item)
            skipped.append(item)
            continue

        parsed[ucode] += 1

        with open(path / f".{ucode}.json", "w", encoding="utf8") as file:
            json.dump(TEMPLATE, file, indent=True)

        with open(path / f"{ucode}.txt", "w", encoding="utf8") as file:
            file.write(char)

        LOGGER.info("Generated %s: %s \t%s \t'%s'", ucode, char, abbrv, note)

    # duplicates information
    no_duplicates = True
    for ucode, count in parsed.items():
        if count > 1:
            LOGGER.warning("Duplicate unicode: %s", ucode)
            no_duplicates = False
    if no_duplicates:
        LOGGER.info("No duplicates detected ✔.")

    if skipped:
        LOGGER.warning("Skipped %d items.", len(skipped))
        for item in skipped:
            LOGGER.warning("Skipped: %s", item)
    else:
        LOGGER.info("No items skipped ✔.")

    LOGGER.info("Installed %s in %s", filename, path)


# In[5]:


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    set_sendmode()
    gerenerate_phrases("icons.csv", "julia_unicode")
    gerenerate_phrases("icons-custom.csv", "custom_unicode")
    generate_help()
    LOGGER.info(r"Finished Installation. Restart AutoKey to enable.")

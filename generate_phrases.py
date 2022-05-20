#!/usr/bin/env python3
# coding: utf-8

# In[1]:

import csv
import json
import logging
import sys
from pathlib import Path
from string import ascii_letters, digits, hexdigits
from typing import Optional

# In[2]:
# Globals / Constants / Templates

LOGGER = logging.getLogger(__name__)
BASE_PATH = Path.home().joinpath(".config/autokey/data/")


if not BASE_PATH.exists():
    print(f"{BASE_PATH} does not exist. Will generate files locally instead.")
    BASE_PATH = Path.cwd()
else:
    print(f"Found autokey directory at {BASE_PATH}.")

UNICODE_PATTERN = ("U", "+") + (hexdigits,) * 5
ABBRV_CHARS = ascii_letters + digits + ";,:^/_+-=()!|*~%"

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
    return len(s) == 6 and all(c in cs for c, cs in zip(s, UNICODE_PATTERN))


def is_abbrv(s: str) -> bool:
    """Check if string is a valid abbreviation."""
    return len(s) > 1 and s[0] == "\\" and all(c in ABBRV_CHARS for c in s[1:])


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


def set_sendMode():
    """Ask the user which sendmode to use."""
    sendMode = query_choice(
        question="How should character substitutions be performed?",
        choices=[r"<ctrl>+v", r"<ctrl>+<shift>+v", r"<shift>+<insert>"],
    )

    TEMPLATE["sendMode"] = sendMode


def load_icons(fname):
    with open(fname, "r", encoding="utf8") as csvfile:
        # scraped from https://docs.julialang.org/en/v1/manual/unicode-input/
        reader_obj = csv.reader(csvfile, delimiter=";")
        data = list(reader_obj)
    return data


def generate_help():
    with open(BASE_PATH.joinpath("julia_unicode_help.py"), "w") as file:
        file.write(HELPSCRIPT)

    with open(BASE_PATH.joinpath("julia_unicode_help.json"), "w") as file:
        json.dump(HELPCONFIG, file, indent=True)

    LOGGER.info("Created help script in %s", BASE_PATH)
    LOGGER.info(r"Type '\help'+[SPACE] for list of all abbreviations.")


def gerenerate_phrases(filename: str, target_dir: str):
    """Read the icons from filename and create phrases files in target_dir."""
    data = load_icons(filename)
    path = BASE_PATH.joinpath(target_dir)
    path.mkdir(exist_ok=True)

    try:
        ucode, char, abbrv, note = next(iter(data[1:]))
    except BaseException as E:
        print(next(iter(data[1:])))
        raise E

    for ucode, char, abbrv, note in data[1:]:
        # sometimes multiple abbreviations exist
        abbrvs: list[str] = [abb.strip(" ") for abb in abbrv.split(", ")]

        for abb in abbrvs:
            assert is_abbrv(abb), f"{abb} is not valid abbreviation."

        name = abbrvs[0][1:].replace("/", "")  # remove '/' for valid filenames

        # add space at the end, otherwise \delta cannot be typed as \del exists
        abbrvs = [abb + " " for abb in abbrvs]
        TEMPLATE["abbreviation"]["abbreviations"] = abbrvs
        TEMPLATE["description"] = note

        with open(path.joinpath(f".{name}.json"), "w", encoding="utf8") as file:
            json.dump(TEMPLATE, file, indent=True)

        with open(path.joinpath(f"{name}.txt"), "w", encoding="utf8") as file:
            file.write(char)
    LOGGER.info("Insalled %s in %s", filename, path)


# In[5]:


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    set_sendMode()
    gerenerate_phrases("icons.csv", "julia_unicode")
    gerenerate_phrases("icons-custom.csv", "custom_unicode")
    generate_help()
    LOGGER.info(r"Finished Installation. Restart AutoKey to enable.")

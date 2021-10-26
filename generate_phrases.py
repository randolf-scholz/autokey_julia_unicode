#!/usr/bin/env python3
# coding: utf-8

# In[1]:

import csv
import json
import sys
from pathlib import Path
from string import ascii_letters, digits, hexdigits
from typing import Optional

# In[2]:

ABBRV_CHARS = ascii_letters + digits + ":^/_+-=()!"
UNICODE_PATTERN = ("U", "+") + (hexdigits,) * 5

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


# In[4]:


def __main__():
    BASE_PATH = Path.home().joinpath(".config/autokey/data/")

    with open("icons.csv", "r") as csvfile:
        # scraped from https://docs.julialang.org/en/v1/manual/unicode-input/
        stream = csv.reader(csvfile, delimiter=";")
        data = list(stream)
        header = data[0]
        unicodes, chars, abbrvs, notes = list(zip(*data[1:]))

    if not BASE_PATH.exists():
        print(f"{BASE_PATH} does not exist. Will generate files locally instead.")
        BASE_PATH = Path.cwd()
    else:
        print(f"Found autokey directory at {BASE_PATH}.")

    PATH = BASE_PATH.joinpath("julia_unicode")
    PATH.mkdir(exist_ok=True)

    sendMode = query_choice(
        question="How should character substitutions be performed?",
        choices=[r"<ctrl>+v", r"<ctrl>+<shift>+v", r"<shift>+<insert>"],
    )

    TEMPLATE["sendMode"] = sendMode

    for ucode, char, abbrv, note in data[1:]:
        abbrvs = abbrv.split(", ")  # sometimes multiple abbreviations exist
        for abb in abbrvs:
            assert is_abbrv(abb), f"{abb} is not valid abbreviation."

        name = abbrvs[0][1:].replace("/", "")  # remove '/' for valid filenames

        # add space at the end, otherwise \delta cannot be typed as \del exists
        abbrvs = [abb + " " for abb in abbrvs]
        TEMPLATE["abbreviation"]["abbreviations"] = abbrvs
        TEMPLATE["description"] = note

        with open(f"{PATH}/.{name}.json", "w") as file:
            json.dump(TEMPLATE, file, indent=True)

        with open(f"{PATH}/{name}.txt", "w") as file:
            file.write(char)

    with open(f"{PATH}/.julia_unicode_help.json", "w") as file:
        json.dump(HELPCONFIG, file, indent=True)

    with open(f"{PATH}/julia_unicode_help.py", "w") as file:
        file.write(HELPSCRIPT)

    print(r"Finished Installation. Restart AutoKey to enable.")
    print(r"Type '\help'+[SPACE] for list of all abbreviations.")


# In[5]:


if __name__ == "__main__":
    __main__()

#!/usr/bin/env python3
# coding: utf-8

# In[1]:


import csv
import json
from pathlib import Path
from string import hexdigits, ascii_letters, digits
import logging


# In[2]:
# Globals / Constants / Templates

LOGGER = logging.getLogger(__name__)
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
    "sendMode": "<shift>+<insert>",
    "showInTrayMenu": False,
    "type": "phrase",
    "usageCount": 0,
}

BASE_PATH = Path.home().joinpath(".config/autokey/data/")

if not BASE_PATH.exists():
    print(F"{BASE_PATH} does not exist. Will generate files locally instead.")
    BASE_PATH = Path.cwd()
else:
    print(F"Found autokey directory at {BASE_PATH}.")


# In[3]:
# Helper functions


def load_icons(fname):
    with open(fname, "r", encoding="utf8") as csvfile:
        # scraped from https://docs.julialang.org/en/v1/manual/unicode-input/
        reader_obj = csv.reader(csvfile, delimiter=";")
        data = list(reader_obj)
    return data

UNICODE_PATTERN = ("U", "+") + (hexdigits,)*5
def is_unicode(s):
    return len(s) == 6 and all(c in cs for c, cs in zip(s, UNICODE_PATTERN))

ABBRV_CHARS = ascii_letters + digits + ":^/_+-=()!|"
def is_abbrv(s):
    return len(s) > 1 and s[0] == "\\" and all(c in ABBRV_CHARS for c in s[1:])

# In[4]:


# In[5]:

def gerenerate_phrases(filename: str, target_dir: str):
    """Read the icons from filename and create phrases files in subdirectory "target_dir"."""
    data = load_icons(filename)
    path = BASE_PATH.joinpath(target_dir)
    path.mkdir(exist_ok=True)

    for ucode, char, abbrv, note in data[1:]:
        # sometimes multiple abbreviations exist
        abbrvs = [abb.strip(" ") for abb in abbrv.split(",")]

        for abb in abbrvs:
            assert is_abbrv(abb), F"{abb} is not valid abbreviation."

        name = abbrvs[0][1:].replace("/", "")  # remove '/' for valid filenames

        # add space at the end, otherwise \delta cannot be typed as \del exists
        abbrvs = [abb+" " for abb in abbrvs]
        TEMPLATE['abbreviation']['abbreviations'] = abbrvs
        TEMPLATE['description'] = note

        with open(path.joinpath(F".{name}.json"), "w", encoding="utf8") as file:
            json.dump(TEMPLATE, file, indent=True)

        with open(path.joinpath(F"{name}.txt"), "w", encoding="utf8") as file:
            file.write(char)
    LOGGER.info("Insalled %s in %s", filename, path)


# In[6]:


def generate_help():
    HELPSCRIPT = """
    import webbrowser
    webbrowser.open("https://docs.julialang.org/en/v1/manual/unicode-input/")
    """

    HELPCONFIG = {
        "type": "script",
        "description": "Help for Julia Unicode",
        "store": {},
        "modes": [
            1
        ],
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
            "wordChars": "[\\w]"
        },
        "hotkey": {
            "modifiers": [],
            "hotKey": None,
        },
        "filter": {
            "regex": None,
            "isRecursive": False,
        }
    }

    with open(BASE_PATH.joinpath('julia_unicode_help.py'), "w") as file:
        file.write(HELPSCRIPT)

    with open(BASE_PATH.joinpath('julia_unicode_help.json'), "w") as file:
        json.dump(HELPCONFIG, file, indent=True)

    LOGGER.info("Created help script in %s", BASE_PATH)
    LOGGER.info(r"Type '\help'+[SPACE] for list of all abbreviations.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    gerenerate_phrases("icons.csv", "julia_unicode")
    gerenerate_phrases("icons-custom.csv", "custom_unicode")
    generate_help()
    LOGGER.info(r"Finished Installation. Restart AutoKey to enable.")

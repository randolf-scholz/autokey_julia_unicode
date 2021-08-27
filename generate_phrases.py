#!/usr/bin/env python3
# coding: utf-8

# In[1]:


import csv
import json
from pathlib import Path
from string import hexdigits, ascii_letters, digits


# In[2]:


with open("icons.csv", "r") as csvfile:
    # scraped from https://docs.julialang.org/en/v1/manual/unicode-input/
    stream = csv.reader(csvfile, delimiter=";")
    data = [line for line in stream]
    header = data[0]
    unicodes, chars, abbrvs, notes = list(zip(*data[1:]))


# In[3]:


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


# In[4]:


ABBRV_CHARS = ascii_letters + digits + ":^/_+-=()!"
UNICODE_PATTERN = ("U", "+") + (hexdigits,)*5


def is_unicode(s):
    return len(s) == 6 and all(c in cs for c, cs in zip(s, UNICODE_PATTERN))


def is_abbrv(s):
    return len(s) > 1 and s[0] == "\\" and all(c in ABBRV_CHARS for c in s[1:])


# In[5]:


BASE_PATH = Path.home().joinpath(".config/autokey/data/")

if not BASE_PATH.exists():
    print(F"{BASE_PATH} does not exist. Will generate files locally instead.")
    BASE_PATH = Path.cwd()
else:
    print(F"Found autokey directory at {BASE_PATH}.")

PATH = BASE_PATH.joinpath("julia_unicode")
PATH.mkdir(exist_ok=True)

for ucode, char, abbrv, note in data[1:]:
    abbrvs = abbrv.split(", ")  # sometimes multiple abbreviations exist
    for abb in abbrvs:
        assert is_abbrv(abb), F"{abb} is not valid abbreviation."

    name = abbrvs[0][1:].replace("/", "")   # remove '/' for valid filenames

    # add space at the end, otherwise \delta cannot be typed as \del exists
    abbrvs = [abb+" " for abb in abbrvs]
    TEMPLATE['abbreviation']['abbreviations'] = abbrvs
    TEMPLATE['description'] = note

    with open(F"{PATH}/.{name}.json", "w") as file:
        json.dump(TEMPLATE, file, indent=True)

    with open(F"{PATH}/{name}.txt", "w") as file:
        file.write(char)

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

with open(F"{PATH}/.julia_unicode_help.json", "w") as file:
    json.dump(HELPCONFIG, file, indent=True)

with open(F"{PATH}/julia_unicode_help.py", "w") as file:
    file.write(HELPSCRIPT)

print(r"Finished Installation. Restart AutoKey to enable.")
print(r"Type '\help'+[SPACE] for list of all abbreviations.")

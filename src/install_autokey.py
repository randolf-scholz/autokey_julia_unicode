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
from collections import defaultdict
from collections.abc import Iterator, Sequence
from enum import StrEnum
from pathlib import Path
from typing import Any, Final, Literal, NamedTuple, Self, TypeGuard

type JSON = dict[str, Any]
LOGGER = logging.getLogger(__name__)
BUILD_DIR: Final[Path] = Path(__file__).resolve().parents[1] / "build" / "autokey"
ASSETS_DIR: Final[Path] = Path(__file__).resolve().parent / "assets"
SEND_MODES: Final[dict[int, str]] = {
    0: r"<ctrl>+v",
    1: r"<ctrl>+<shift>+v",
    2: r"<shift>+<insert>",
}


class Header(StrEnum):
    """TSV column names for Unicode samples."""

    CODEPOINTS = "Code point(s)"
    CHARACTERS = "Character(s)"
    ABBREVIATIONS = "Tab completion sequence(s)"
    DESCRIPTION = "Unicode name(s)"


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
            and (
                ("\ufe00" <= s[1] <= "\ufe0f")  # variation selector
                or ("\u0300" <= s[1] <= "\u036f")  # combining character
            )
        )
    )


class CodePoint(str):
    """Unicode code type (like U+)."""

    PATTERN = re.compile(r"U\+[0-9A-F]{4,6}")
    """Regex pattern for unicode codes."""

    def __new__(cls, value: str) -> Self:
        if not isinstance(value, str) or CodePoint.PATTERN.fullmatch(value) is None:
            raise ValueError(f"{value!r} is not a valid unicode code.")
        return super().__new__(cls, value)

    @property
    def hex(self) -> int:
        return int(self[2:], 16)  # ruff: ignore[FURB166]


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
        if not isinstance(value, str) or Abbreviation.PATTERN.fullmatch(value) is None:
            raise ValueError(
                f"{value!r} is not a valid abbreviation."
                "\nAbbrevations must begin with a backslash and terminate with a space."
                "\nInside the abbrevations only the printable ascii characters x21-x7e are allowed,"
                " except backslash x5C."
            )
        return super().__new__(cls, value)


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


def query_choice[T](
    question: str = "Please pick one of the following:",
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


def load_icons(fname: str | Path, /) -> Iterator[UnprocessedSample]:
    """Yield TSV icons by column name, ignoring additional columns."""
    LOGGER.info("Parsing %s", fname)

    with open(fname, encoding="utf8", newline="") as tsv_file:
        reader = csv.DictReader(tsv_file, delimiter="\t", quoting=csv.QUOTE_NONE)
        if missing_columns := set(Header) - set(reader.fieldnames or ()):
            raise ValueError(
                f"Missing columns in {fname}: {', '.join(sorted(missing_columns))}"
            )

        for row in reader:
            if missing_values := [
                column.value for column in Header if row[column] is None
            ]:
                raise ValueError(
                    f"Missing values in {fname} at line {reader.line_num}: {missing_values}"
                )
            yield UnprocessedSample(
                ucode=row[Header.CODEPOINTS],
                char=row[Header.CHARACTERS],
                abbreviations=row[Header.ABBREVIATIONS],
                description=row[Header.DESCRIPTION],
            )


def process_icons(fname: str | Path, /) -> list[UnicodeSample]:
    """Load and validate TSV samples, skipping unsupported glyphs and missing abbreviations."""
    samples: list[UnicodeSample] = []
    skipped: list[tuple[UnprocessedSample, str]] = []  # items

    for item in load_icons(fname):
        ucode, char, raw_abb, description = item
        parsed_ucodes = parse_codepoints(ucode)

        # guard against invalid character
        if not is_glyph(char):
            LOGGER.debug("Invalid character: %s=%s", item.ucode, item.char)
            skipped.append(
                (
                    item,
                    f"Invalid character {char!r}={str_to_codepoints(char)}",
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


def write_asset(
    destination: Path,
    /,
    *,
    payload: bytes,
    metadata: JSON,
    duplicates: Literal["error", "skip"] = "error",
) -> bool:
    """Write a payload/metadata pair, returning False for a skipped duplicate."""
    metadata_path = destination.with_suffix(".json")

    for path in (destination, metadata_path):
        if path.exists():
            if duplicates == "skip":
                return False
            raise FileExistsError(f"File {path} already exists.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)
    with metadata_path.open("w", encoding="utf8") as file:
        json.dump(metadata, file, indent=True)
    return True


def generate_codes(
    directory: str | Path,
    *,
    target_dir: Path,
    template: JSON,
    sendmode: str,
    duplicates: Literal["error", "skip"],
) -> None:
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

    num_created = 0
    all_abbreviations: dict[Abbreviation, list[Glyph]] = defaultdict(list)
    skipped_duplicates: list[UnicodeSample] = []

    # iterate over all .tsv files in the directory
    for filename in sorted(folder.glob("*.tsv")):
        LOGGER.info("-" * 80)
        for sample in process_icons(filename):
            if not write_asset(
                target_dir / f"{sample.name}.txt",
                payload=sample.glyph.encode("utf8"),
                metadata=_merge_dicts(
                    template,
                    {
                        "sendMode": sendmode,
                        "abbreviation": {"abbreviations": sample.abbreviations},
                        "description": sample.description,
                    },
                ),
                duplicates=duplicates,
            ):
                skipped_duplicates.append(sample)
                LOGGER.info(
                    "Skipped duplicate character: %s (%s)", sample.glyph, sample.name
                )
                continue

            LOGGER.debug("Registered %s", sample)
            num_created += 1
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

    LOGGER.info("✅️ %d unique glyphs registered.", num_created)


def prepare_build_directory(
    directories: Sequence[str | Path],
    target_dir: Path,
) -> None:
    """Validate paths before removing the entire previous build."""
    folders = [Path(directory).resolve() for directory in directories]
    names = [folder.name for folder in folders] + [
        "latex_snippets",
        "special_chars",
        "custom_scripts",
    ]
    if len(set(names)) != len(names):
        raise ValueError("Source directories must have distinct folder names.")
    for folder in folders:
        if not folder.is_dir():
            raise NotADirectoryError(f"{folder} is not a directory.")
    for path in (BUILD_DIR, *(BUILD_DIR / name for name in names)):
        if path.is_symlink():
            raise ValueError(f"Build directory {path} must not be a symbolic link.")
        if path.exists() and not path.is_dir():
            raise NotADirectoryError(f"{path} is not a directory.")
    build_dir = BUILD_DIR.resolve()
    protected = folders + [ASSETS_DIR.parent] + [target_dir / name for name in names]
    for path in protected:
        path = path.resolve()
        if build_dir.is_relative_to(path) or path.is_relative_to(build_dir):
            raise ValueError(f"Build directory {build_dir} overlaps {path}.")
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True)


def build_icons(
    directories: Sequence[str | Path],
    *,
    sendmode: str,
    duplicates: Literal["error", "skip"],
) -> None:
    """Build the requested TSV collections in BUILD_DIR."""
    with (ASSETS_DIR / "templates" / "phrase.json").open(encoding="utf8") as file:
        template: JSON = json.load(file)
    for directory in directories:
        generate_codes(
            directory,
            target_dir=BUILD_DIR,
            template=template,
            sendmode=sendmode,
            duplicates=duplicates,
        )


def validate_metadata(metadata: JSON, source: Path) -> None:
    """Require a description and abbreviation list, reporting the invalid field."""
    if not isinstance(metadata.get("description"), str):
        raise ValueError(  # noqa: TRY004 - invalid configuration data
            f"Invalid metadata in {source}: description must be a string."
        )
    abbreviation = metadata.get("abbreviation")
    if not isinstance(abbreviation, dict):
        raise ValueError(  # noqa: TRY004 - invalid configuration data
            f"Invalid metadata in {source}: abbreviation must be a table."
        )
    abbreviations = abbreviation.get("abbreviations")
    if not isinstance(abbreviations, list) or not all(
        isinstance(value, str) for value in abbreviations
    ):
        raise ValueError(
            f"Invalid metadata in {source}: "
            "abbreviation.abbreviations must be a list of strings."
        )


def build_phrases(source_dir: Path, *, sendmode: str) -> None:
    """Build TOML phrase assets in BUILD_DIR."""
    build_dir = BUILD_DIR / source_dir.name

    template_file = source_dir.parent / "templates" / "phrase.json"
    with template_file.open(encoding="utf8") as file:
        template: JSON = json.load(file)

    LOGGER.info("Building phrases in %s.", build_dir)
    for source in sorted(source_dir.rglob("*.toml")):
        with source.open("rb") as file:
            updates = tomllib.load(file)
        payload = updates.pop("payload", None)
        if not isinstance(payload, str):
            raise ValueError(  # noqa: TRY004 - invalid configuration data
                f"Invalid snippet {source}: payload must be a string."
            )
        metadata = _merge_dicts(
            template,
            {"description": source.stem} | updates | {"sendMode": sendmode},
        )
        validate_metadata(metadata, source)
        relative_path = source.relative_to(source_dir)
        write_asset(
            build_dir / relative_path.with_suffix(".txt"),
            payload=payload.encode("utf8"),
            metadata=metadata,
        )


def _merge_dicts(template: JSON, updates: JSON) -> JSON:
    """Merge nested dictionaries, replacing lists and scalar values."""
    merged = template | updates
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(template.get(key), dict):
            merged[key] = _merge_dicts(template[key], value)
    return merged


def build_custom_scripts() -> None:
    """Build Python scripts and metadata from TOML overrides in BUILD_DIR."""
    source_dir = ASSETS_DIR / "custom_scripts"
    build_dir = BUILD_DIR / source_dir.name

    template_file = source_dir.parent / "templates" / "script.json"
    with template_file.open(encoding="utf8") as file:
        template: JSON = json.load(file)

    LOGGER.info("Building custom scripts in %s.", build_dir)
    for source in sorted(source_dir.rglob("*.toml")):
        with source.open("rb") as file:
            updates = tomllib.load(file)
        metadata = _merge_dicts(template, updates)
        validate_metadata(metadata, source)
        if not source.with_suffix(".py").is_file():
            raise FileNotFoundError(f"Missing Python script for {source}.")
        write_asset(
            build_dir / source.relative_to(source_dir).with_suffix(".py"),
            payload=source.with_suffix(".py").read_bytes(),
            metadata=metadata,
        )


def install_build(target_dir: Path) -> None:
    """Move all built collections into AutoKey, restoring backups on failure."""
    collections = sorted(BUILD_DIR.iterdir())
    existing = [
        source.name
        for source in collections
        if (target_dir / source.name).exists()
        or (target_dir / source.name).is_symlink()
    ]
    if existing and not query_choice(
        f"Replace existing collections in {target_dir}: {', '.join(existing)}?",
        choices=[False, True],
    ):
        LOGGER.info("Installation cancelled; build retained in %s.", BUILD_DIR)
        return

    target_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".autokey-install-", dir=target_dir
    ) as temporary:
        backup_dir = Path(temporary)
        attempted: list[Path] = []
        try:
            for source in collections:
                destination = target_dir / source.name
                if destination.exists() or destination.is_symlink():
                    destination.rename(backup_dir / source.name)
                attempted.append(source)
                shutil.move(source, destination)
        except (OSError, KeyboardInterrupt):
            for source in reversed(attempted):
                destination = target_dir / source.name
                if not source.exists():
                    shutil.move(destination, source)
                elif destination.exists():
                    # A cross-filesystem move can leave an incomplete copy.
                    shutil.rmtree(destination)
            for backup in backup_dir.iterdir():
                backup.rename(target_dir / backup.name)
            raise
    LOGGER.info(
        "Installed AutoKey assets in %s. Restart AutoKey to enable them!", target_dir
    )


def main() -> None:
    r"""Install function."""
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
        help="Build all AutoKey assets without installing them.",
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

    # if sendmode is missing, ask user
    sendmode = (
        SEND_MODES[args.sendmode]
        if args.sendmode is not None
        else query_choice(
            question="How should character substitutions be performed?",
            choices=SEND_MODES,
        )
    )

    target_dir = (args.autokey_directory / args.target_directory).resolve()

    prepare_build_directory(args.source_directories, target_dir)
    build_icons(
        args.source_directories,
        sendmode=sendmode,
        duplicates=args.duplicates,
    )
    build_phrases(ASSETS_DIR / "latex_snippets", sendmode=sendmode)
    build_phrases(ASSETS_DIR / "special_chars", sendmode=sendmode)
    build_custom_scripts()

    if args.build_only:
        LOGGER.info("Build complete in %s; installation skipped.", BUILD_DIR)
        return

    check_autokey_version()
    if not detected_directory.exists():
        LOGGER.warning("Autokey directory not found. Installing into %s.", target_dir)
    install_build(target_dir)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()

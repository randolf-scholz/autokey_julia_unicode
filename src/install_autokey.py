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
import tomllib
from collections import defaultdict
from collections.abc import Generator, Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from enum import StrEnum
from pathlib import Path
from tempfile import mkdtemp
from typing import Any, Final, Literal, NamedTuple, Self, TypeGuard

type JSON = dict[str, Any]
LOGGER = logging.getLogger(__name__)
PROJECT_DIR: Final[Path] = Path(__file__).resolve().parents[1]
DATA_DIR: Final[Path] = PROJECT_DIR / "data"
AUTOKEY_DIR: Final[Path] = Path.home() / ".config" / "autokey" / "data"
DEFAULT_TARGET_DIR: Final[Path] = AUTOKEY_DIR / "julia_unicode"
BUILD_DIR: Final[Path] = PROJECT_DIR / "build" / "autokey"
ASSETS_DIR: Final[Path] = DATA_DIR / "autokey"
LOG_FILENAME: Final[str] = "install.log"


class SendMode(StrEnum):
    """Keyboard shortcuts used to paste character substitutions."""

    CTRL_V = "<ctrl>+v"
    CTRL_SHIFT_V = "<ctrl>+<shift>+v"
    SHIFT_INSERT = "<shift>+<insert>"


SEND_MODES: Final[Mapping[int, str]] = {i: m.value for i, m in enumerate(SendMode)}


class ConsoleFormatter(logging.Formatter):
    """Color summary fields on terminals without modifying the shared log record."""

    def __init__(self, *, color: bool) -> None:
        super().__init__("%(levelname)s: %(message)s")
        self.color = color

    def format(self, record: logging.LogRecord) -> str:
        summary: tuple[str, list[tuple[str, int]]] | None = getattr(
            record, "summary", None
        )
        if not self.color or summary is None:
            return super().format(record)
        path, fields = summary
        colored_fields = ", ".join(
            f"\033[{color}m{text}\033[0m" for text, color in fields
        )
        colored = logging.makeLogRecord(record.__dict__)
        colored.msg = f"\033[34m{path}\033[0m: {colored_fields}."
        colored.args = ()
        return super().format(colored)


def log_build_summary(
    path: Path,
    created: int,
    *,
    unit: str = "phrases",
    skipped: int | None = None,
    duplicates: int | None = None,
    duplicate_abbreviations: int | None = None,
) -> None:
    """Log a plain summary with optional color metadata for the console."""
    if path.is_relative_to(PROJECT_DIR):
        path = path.relative_to(PROJECT_DIR)
    fields = [(f"{created} {unit}", 32)]
    if skipped is not None:
        fields.append((f"{skipped} skipped", 33 if skipped else 90))
    if duplicates is not None:
        fields.append(
            (f"{duplicates} duplicate characters skipped", 31 if duplicates else 90)
        )
    if duplicate_abbreviations is not None:
        fields.append(
            (
                f"{duplicate_abbreviations} duplicate abbreviations",
                31 if duplicate_abbreviations else 90,
            )
        )
    LOGGER.info(
        "%s: %s.",
        path,
        ", ".join(text for text, _ in fields),
        extra={"summary": (str(path), fields)},
    )


@contextmanager
def installation_logging(build_dir: Path, *, verbose: bool) -> Generator:
    """Show summaries on stderr and retain all debug records in the build log."""
    if build_dir.is_symlink():
        raise OSError(f"Build directory {build_dir} must not be a symlink.")
    build_dir.mkdir(parents=True, exist_ok=True)
    log_path = build_dir / LOG_FILENAME
    if log_path.is_symlink():
        log_path.unlink()

    file_handler = logging.FileHandler(log_path, mode="w", encoding="utf8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    )
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(
        ConsoleFormatter(
            color=(
                console_handler.stream.isatty()
                and "NO_COLOR" not in os.environ
                and os.environ.get("TERM") != "dumb"
            )
        )
    )

    previous = LOGGER.level, LOGGER.handlers, LOGGER.propagate
    LOGGER.setLevel(logging.DEBUG)
    LOGGER.handlers = [console_handler, file_handler]
    LOGGER.propagate = False
    try:
        LOGGER.info("Full log: %s", log_path)
        yield
    except BaseException:
        LOGGER.debug("Installer interrupted or failed.", exc_info=True)
        raise
    finally:
        LOGGER.setLevel(previous[0])
        LOGGER.handlers = previous[1]
        LOGGER.propagate = previous[2]
        file_handler.close()
        console_handler.close()


class Header(StrEnum):
    """TSV column names for Unicode samples."""

    CODEPOINTS = "code_points"
    CHARACTERS = "chars"
    ABBREVIATIONS = "tab_completions"
    DESCRIPTION = "unicode_name"


def check_autokey_version(search_path: str = os.defpath, /) -> None:
    """Require system AutoKey >=0.96.0 when its version can be determined."""
    for command in ("autokey-gtk", "autokey-qt"):
        # Use the system search path so a virtual environment cannot shadow AutoKey.
        if (executable := shutil.which(command, path=search_path)) is None:
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

        if (match := re.search(r"\b(\d+)\.(\d+)\.(\d+)\b", result.stdout)) is None:
            continue

        if tuple(map(int, match.groups())) < (0, 96, 0):
            raise SystemExit(f"AutoKey >=0.96.0 is required; found {match[0]}.")

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
    """Unicode code point normalized to U+ followed by at least four hex digits."""

    PATTERN = re.compile(r"U\+[0-9A-F]{4,6}")
    """Regex pattern for unicode codes."""

    def __new__(cls, value: str) -> Self:
        if not isinstance(value, str) or CodePoint.PATTERN.fullmatch(value) is None:
            raise ValueError(f"{value!r} is not a valid unicode code.")
        # Strip excess leading zeros while keeping at least four uppercase hex digits.
        point = int(value.removeprefix("U+"), 16)
        if point > 0x10FFFF or 0xD800 <= point <= 0xDFFF:
            raise ValueError(f"{value!r} is not a Unicode scalar value.")
        normalized = f"U+{point:04X}"
        return super().__new__(cls, normalized)


def parse_codepoints(value: str, /) -> list[CodePoint]:
    """Read the schema's comma-space-separated code points."""
    return [CodePoint(code) for code in value.split(", ")]


def str_to_codepoints(s: str, /) -> list[CodePoint]:
    r"""Convert a string to a list of code points.

    Example:
        >>> str_to_codepoints("✅️")
        ['U+2705', 'U+FE0F']
    """
    return [CodePoint(f"U+{ord(c):04X}") for c in s]


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
    if not raw_data:
        return []
    return [Abbreviation(abb + " ") for abb in raw_data.split(", ")]


def query_choice[T](
    question: str = "Please pick one of the following:",
    *,
    choices: list[T] | Mapping[int, T],
    default: int | None = 0,
) -> T:
    """Ask the user to pick an option."""
    options = choices if isinstance(choices, Mapping) else dict(enumerate(choices))

    if default is not None:
        assert default in options, f"Default {default} not in {options}"

    while True:
        try:
            LOGGER.debug(
                "Prompt: %s; choices=%r; default=%r", question, options, default
            )
            print(question)
            for i, option in options.items():
                label = option.value if isinstance(option, StrEnum) else option
                print(f"{i:3d}. {label!r}")
            user_choice = input(f"Enter integer (default: {default}): ")
            LOGGER.debug("User input: %r", user_choice)
        except (KeyboardInterrupt, SystemExit) as exc:
            exc.add_note("Operation aborted. Exiting.")
            raise
        try:
            choice = options[
                default
                if user_choice == "" and default is not None
                else int(user_choice)
            ]
            LOGGER.debug("Selected: %r", choice)
            return choice
        except (KeyError, ValueError):
            LOGGER.debug("Did not understand input: %r", user_choice)
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
    """Yield unquoted TSV icons, reconstructing omitted chars from code points."""
    LOGGER.debug("Parsing %s", fname)

    with open(fname, encoding="utf8", newline="") as tsv_file:
        reader = csv.DictReader(
            tsv_file,
            delimiter="\t",
            quoting=csv.QUOTE_NONE,
            quotechar=None,
        )
        if missing_cols := sorted(set(Header) - set(reader.fieldnames or ())):
            raise ValueError(f"Missing columns in {fname}: {', '.join(missing_cols)}")

        for row in reader:
            if missing_vals := [col.value for col in Header if row[col] is None]:
                raise ValueError(
                    f"Missing values in {fname} at line {reader.line_num}: {missing_vals}"
                )
            chars = row[Header.CHARACTERS]
            if not chars:
                try:
                    chars = "".join(
                        chr(int(point.removeprefix("U+"), 16))
                        for point in parse_codepoints(row[Header.CODEPOINTS])
                    )
                except ValueError as error:
                    raise ValueError(
                        f"{fname}:{reader.line_num}: invalid code_points: {error}"
                    ) from error
            yield UnprocessedSample(
                ucode=row[Header.CODEPOINTS],
                char=chars,
                abbreviations=row[Header.ABBREVIATIONS],
                description=row[Header.DESCRIPTION],
            )


class ProcessedIcons(NamedTuple):
    """Validated samples and the number of omitted source rows."""

    samples: list[UnicodeSample]
    skipped: int


def process_icons(fname: str | Path, /) -> ProcessedIcons:
    """Load and validate TSV samples, skipping unsupported glyphs and missing abbreviations."""
    samples: list[UnicodeSample] = []
    skipped: list[tuple[UnprocessedSample, str]] = []  # items

    for item in load_icons(fname):
        ucode, char, raw_abb, description = item
        parsed_ucodes = parse_codepoints(ucode)

        # guard against invalid character
        if not is_glyph(char):
            LOGGER.debug("Invalid character: %s=%s", item.ucode, item.char)
            reason = f"Invalid character {char!r}={str_to_codepoints(char)}"
            skipped.append((item, reason))
            continue

        try:  # guard against invalid abbreviation
            abbreviations = make_abbreviations(raw_abb)
        except ValueError as err:
            raise ValueError(f"Invalid abbreviation: {item}") from err
        else:
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
        LOGGER.debug("Skipped: %s, reason=%r", item, reason)
    LOGGER.debug(
        "Processed %s: %d accepted, %d skipped.", fname, len(samples), len(skipped)
    )
    return ProcessedIcons(samples, len(skipped))


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
    LOGGER.debug("Wrote %s and %s", destination, metadata_path)
    return True


def build_phrases_from_tsv(
    source_dir: str | Path,
    build_dir: Path,
    *,
    template: JSON,
    send_mode: SendMode,
    duplicates: Literal["error", "skip"],
) -> None:
    """Generate an icon collection in a fresh subdirectory of build_dir."""
    source_dir = Path(source_dir)
    if not source_dir.exists():
        raise FileNotFoundError(f"{source_dir} does not exist.")
    if not source_dir.is_dir():
        raise NotADirectoryError(f"{source_dir} is not a directory.")

    target_dir = build_dir / source_dir.name
    target_dir.mkdir(parents=True)

    LOGGER.debug("Building icons from %s in %s", source_dir, target_dir)

    num_created = 0
    all_abbreviations: dict[Abbreviation, list[Glyph]] = defaultdict(list)
    skipped_duplicates: list[UnicodeSample] = []

    # iterate over all .tsv files in the directory
    for filename in sorted(source_dir.glob("*.tsv")):
        file_created = 0
        file_duplicates = 0
        processed = process_icons(filename)
        for sample in processed.samples:
            if not write_asset(
                target_dir / f"{sample.name}.txt",
                payload=sample.glyph.encode("utf8"),
                metadata=_merge_dicts(
                    template,
                    {
                        "sendMode": str(send_mode),
                        "abbreviation": {"abbreviations": sample.abbreviations},
                        "description": sample.description,
                    },
                ),
                duplicates=duplicates,
            ):
                skipped_duplicates.append(sample)
                file_duplicates += 1
                LOGGER.debug(
                    "Skipped duplicate character: %s (%s)", sample.glyph, sample.name
                )
                continue

            LOGGER.debug("Registered %s", sample)
            num_created += 1
            file_created += 1
            for abb in sample.abbreviations:
                all_abbreviations[abb].append(sample.glyph)

        log_build_summary(
            filename,
            file_created,
            skipped=processed.skipped,
            duplicates=file_duplicates,
        )

    # check if all abbreviations are unique
    num_duplicates = 0
    for abb, ucodes in all_abbreviations.items():
        if len(ucodes) > 1:
            LOGGER.debug("Duplicate abbreviation: %s -> %s", abb, ucodes)
            num_duplicates += 1
    log_build_summary(
        source_dir,
        num_created,
        unit="glyphs",
        duplicates=len(skipped_duplicates),
        duplicate_abbreviations=num_duplicates,
    )


def validate_metadata(metadata: JSON, source: Path) -> None:
    """Require a description and abbreviation list, reporting the invalid field."""
    if not isinstance(metadata.get("description"), str):
        raise TypeError(f"Invalid metadata in {source}: description must be a string.")

    abbreviation = metadata.get("abbreviation")
    if not isinstance(abbreviation, dict):
        raise TypeError(f"Invalid metadata in {source}: abbreviation must be a table.")

    abbs = abbreviation.get("abbreviations")
    if not isinstance(abbs, list) or not all(isinstance(a, str) for a in abbs):
        raise TypeError(
            f"Invalid metadata in {source}: "
            "abbreviation.abbreviations must be a list of strings."
        )


def build_phrases(source_dir: Path, build_dir: Path, *, send_mode: SendMode) -> None:
    """Build TOML phrase assets in a collection under build_dir."""
    build_dir = build_dir / source_dir.name
    build_dir.mkdir(parents=True)

    template_file = source_dir.parent / "templates" / "phrase.json"
    with template_file.open(encoding="utf8") as file:
        template: JSON = json.load(file)

    LOGGER.debug("Building phrases in %s.", build_dir)
    num_created = 0
    for source in sorted(source_dir.rglob("*.toml")):
        with source.open("rb") as file:
            updates = tomllib.load(file)

        payload = updates.pop("payload", None)
        if not isinstance(payload, str):
            raise TypeError(f"Invalid snippet {source}: payload must be a string.")

        metadata = _merge_dicts(
            template,
            {"description": source.stem} | updates | {"sendMode": str(send_mode)},
        )
        validate_metadata(metadata, source)
        relative_path = source.relative_to(source_dir)
        write_asset(
            build_dir / relative_path.with_suffix(".txt"),
            payload=payload.encode("utf8"),
            metadata=metadata,
        )
        num_created += 1
    log_build_summary(source_dir, num_created)


def _merge_dicts(template: JSON, updates: JSON) -> JSON:
    """Merge nested dictionaries, replacing lists and scalar values."""
    merged = template | updates
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(template.get(key), dict):
            merged[key] = _merge_dicts(template[key], value)
    return merged


def build_custom_scripts(source_dir: Path, build_dir: Path) -> None:
    """Build Python scripts and TOML metadata overrides under build_dir."""
    build_dir = build_dir / source_dir.name
    build_dir.mkdir(parents=True)

    template_file = source_dir.parent / "templates" / "script.json"
    with template_file.open(encoding="utf8") as file:
        template: JSON = json.load(file)

    LOGGER.debug("Building custom scripts in %s.", build_dir)
    num_created = 0
    for source in sorted(source_dir.rglob("*.toml")):
        if not source.with_suffix(".py").is_file():
            raise FileNotFoundError(f"Missing Python script for {source}.")

        with source.open("rb") as file:
            updates = tomllib.load(file)

        metadata = _merge_dicts(template, updates)
        validate_metadata(metadata, source)

        write_asset(
            build_dir / source.relative_to(source_dir).with_suffix(".py"),
            payload=source.with_suffix(".py").read_bytes(),
            metadata=metadata,
        )
        num_created += 1
    log_build_summary(source_dir, num_created, unit="scripts")


def clear_build_assets(build_dir: Path) -> None:
    """Remove generated assets while retaining the current run's log."""
    if build_dir.is_symlink():
        raise OSError(f"Build directory {build_dir} must not be a symlink.")
    build_dir.mkdir(parents=True, exist_ok=True)
    for path in build_dir.iterdir():
        if path.name == LOG_FILENAME:
            continue
        if path.is_symlink() or not path.is_dir():
            path.unlink()
        else:
            shutil.rmtree(path)


def build_assets(
    source_directories: Iterable[str | Path],
    *,
    send_mode: SendMode,
    duplicates: Literal["error", "skip"],
    build_dir: Path = BUILD_DIR,
    assets_dir: Path = ASSETS_DIR,
) -> None:
    """Reset build_dir and build all assets without prompts or installation."""
    clear_build_assets(build_dir)

    template_file = assets_dir / "templates" / "phrase.json"
    with template_file.open(encoding="utf8") as file:
        template: JSON = json.load(file)

    for source in source_directories:
        build_phrases_from_tsv(
            source,
            build_dir,
            template=template,
            send_mode=send_mode,
            duplicates=duplicates,
        )
    build_phrases(assets_dir / "latex_snippets", build_dir, send_mode=send_mode)
    build_phrases(assets_dir / "special_chars", build_dir, send_mode=send_mode)
    build_custom_scripts(assets_dir / "custom_scripts", build_dir)


def validate_install_target(
    target_dir: Path, build_dir: Path, *, autokey_dir: Path
) -> Path:
    """Require a dedicated target separate from the build and AutoKey data root."""
    target_dir = Path(os.path.abspath(target_dir))
    # Resolve parent aliases, preserving a final symlink so it can be replaced.
    target_dir = target_dir.parent.resolve() / target_dir.name
    resolved = target_dir.resolve()
    build_dir = build_dir.resolve()
    if resolved.is_relative_to(build_dir) or build_dir.is_relative_to(resolved):
        raise ValueError(
            f"Installation target {target_dir} must be outside {build_dir} "
            "and must not contain it."
        )
    if autokey_dir.resolve().is_relative_to(resolved):
        raise ValueError(
            f"Installation target {target_dir} must not be the AutoKey data "
            f"directory {autokey_dir} or one of its parents."
        )
    return target_dir


def install_build(target_dir: Path, build_dir: Path) -> None:
    """Select optional assets and replace the dedicated target with a staged build."""
    target_dir = validate_install_target(
        target_dir, build_dir=build_dir, autokey_dir=AUTOKEY_DIR
    )
    if (target_dir.exists() or target_dir.is_symlink()) and not query_choice(
        f"Replace the entire installation directory {target_dir} and all its contents?",
        choices=[False, True],
    ):
        LOGGER.info("Installation cancelled; build retained in %s.", build_dir)
        return

    skipped: list[Path] = []
    for source in sorted((build_dir / "special_chars").rglob("*.txt")):
        payload = source.read_text(encoding="utf8")
        if not query_choice(
            f"Install special character {source.stem} ({payload!r})?",
            choices=[False, True],
        ):
            skipped.append(source.relative_to(build_dir))

    # Stage on the target filesystem; the complete build remains available on failure.
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(mkdtemp(prefix=f".{target_dir.name}-", dir=target_dir.parent))
    staging = temporary / "installation"
    backup = temporary / "previous"
    installed = False
    try:
        shutil.copytree(build_dir, staging, ignore=shutil.ignore_patterns(LOG_FILENAME))
        for relative in skipped:
            (staging / relative).unlink()
            (staging / relative.with_suffix(".json")).unlink()

        if target_dir.exists() or target_dir.is_symlink():
            target_dir.rename(backup)
        try:
            staging.rename(target_dir)
        except BaseException:
            if backup.exists() or backup.is_symlink():
                backup.rename(target_dir)
            raise
        installed = True
    finally:
        if installed or not (backup.exists() or backup.is_symlink()):
            shutil.rmtree(temporary)
        else:
            LOGGER.error(
                "Could not restore the previous installation; retained at %s.", backup
            )

    LOGGER.info(
        "Installed AutoKey assets in %s. Restart AutoKey to enable them!", target_dir
    )
    LOGGER.info(r"Type \help followed by a space to open Julia's Unicode input page.")


def main(argv: Sequence[str] | None = None) -> int:
    r"""Install function."""
    parser = argparse.ArgumentParser(
        description="Install icons for usage with autokey.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=[DATA_DIR / "icons"],
        type=Path,
        help=(
            "Directories whose immediate subdirectories are icon collections "
            f"(default: {DATA_DIR / 'icons'})."
        ),
    )
    parser.add_argument(
        "--sendmode",
        choices=SEND_MODES,
        default=None,
        type=int,
        help=(
            f"How should character substitutions be performed?\n{SEND_MODES}. "
            "Prompt if omitted; build-only defaults to 0."
        ),
    )
    parser.add_argument(
        "--target-directory",
        default="",
        type=str,
        help="Subdirectory of the installation directory; an absolute path overrides it.",
    )
    parser.add_argument(
        "--autokey-directory",
        default=None,
        type=Path,
        help=f"Install location. If omitted, uses {DEFAULT_TARGET_DIR}.",
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

    args = parser.parse_args(argv)

    autokey_directory = args.autokey_directory
    if autokey_directory is None:
        if (
            not args.build_only
            and not Path(args.target_directory).is_absolute()
            and not AUTOKEY_DIR.is_dir()
        ):
            parser.error(
                f"AutoKey data directory {AUTOKEY_DIR} does not exist or is not "
                "a directory. Start AutoKey to initialize it, or provide "
                "--autokey-directory."
            )
        autokey_directory = DEFAULT_TARGET_DIR

    target_dir = validate_install_target(
        autokey_directory / args.target_directory,
        build_dir=BUILD_DIR,
        autokey_dir=AUTOKEY_DIR,
    )

    with installation_logging(BUILD_DIR, verbose=args.verbose):
        source_directories = [
            directory
            for root in args.paths
            for directory in sorted(root.iterdir())
            if directory.is_dir()
        ]

        # Build-only mode needs no interactive choices.
        if args.sendmode is not None:
            send_mode = SEND_MODES[args.sendmode]
        elif args.build_only:
            send_mode = SendMode.CTRL_V
        else:
            send_mode = query_choice(
                question="How should character substitutions be performed?",
                choices=SEND_MODES,
            )

        build_assets(
            source_directories,
            send_mode=SendMode(send_mode),
            duplicates=args.duplicates,
            build_dir=BUILD_DIR,
            assets_dir=ASSETS_DIR,
        )

        if args.build_only:
            LOGGER.info("Build complete in %s; installation skipped.", BUILD_DIR)
            return 0

        check_autokey_version()
        install_build(target_dir, BUILD_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

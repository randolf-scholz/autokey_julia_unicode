#!/usr/bin/env python


import argparse
import hashlib
import os
from pathlib import Path

SOURCE_DIRECTORY = "src"
r"""The source directory where the files are located."""
TARGET_DIRECTORY = "unicode-symbols"
r"""The target directory in the TEXMFHOME tree where the files are copied to."""
SOURCE_PATTERN = {".sty", ".cls", ".tex"}
r"""The extension of the files to be copied to the target directory."""
CWD = Path(__file__).resolve().parent
r"""The current working directory."""


def get_texmf_directory() -> Path:
    """Return the target directory for the installation."""
    # first, check if TEXMFHOME is set
    texmfhome = os.environ.get("TEXMFHOME", "")
    if texmfhome:
        return Path(texmfhome)
    # else, fall back to ~/texmf
    return Path.home() / "texmf"


def get_target_directory() -> Path:
    """Return the target directory (existence guaranteed)."""
    texmf = get_texmf_directory()
    target = texmf / "tex" / "latex" / TARGET_DIRECTORY
    if not target.exists():
        target.mkdir(parents=True)
    return target


def get_source_directory() -> Path:
    """Return the source directory (existence guaranteed)."""
    source_dir = CWD / SOURCE_DIRECTORY
    if source_dir.exists():
        return source_dir.relative_to(CWD)
    raise FileNotFoundError(f"Could not find the source directory {source_dir}.")


def ask_for_overwrite(file: Path, default: bool = True) -> bool:
    """Ask the user whether to overwrite an existing file."""
    msg = f"Overwrite {file}? {'[Y/n]' if default else '[y/N]'}"
    max_retries = 3

    for k in range(max_retries):
        overwrite = input(msg).strip().lower()
        if overwrite in {"y", "yes"}:
            return True
        if overwrite in {"n", "no"}:
            return False
        if overwrite == "":
            return default
        print("Invalid input. Please enter 'y' or 'n'.")

    raise ValueError("Too many retries.")


def copy_file(source: Path, target: Path, overwrite: bool = False) -> None:
    """Copy a file from the source to the target directory."""
    if not target.exists():
        print(f"Copying {source} to {target}.")
        target.write_text(source.read_text())
    if target.exists():
        # check if the files are identical via hash
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        target_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        if source_hash == target_hash:
            # get relative path of source to install.py
            print(f"Skipping {source} (file with same content already exists).")
            return

        # ask for permission to overwrite
        if not overwrite or not ask_for_overwrite(target):
            print(f"Skipping {source}.")
            return

    print(f"Copying {source} to {target}.")
    target.write_text(source.read_text())


def install(overwrite: bool = False) -> None:
    """Install the latex-unicode package."""
    source_dir = get_source_directory()
    target_dir = get_target_directory()

    # iterate over all files in the source directory
    for file in source_dir.iterdir():
        if file.suffix in SOURCE_PATTERN:
            source = source_dir / file.name
            target = target_dir / file.name

            try:
                copy_file(source=source, target=target, overwrite=overwrite)
            except Exception as exc:
                print(f"Error while copying {source} to {target}: {exc}")
                print("Aborting installation.")
                return

    print(f"Installation complete. Files are located in {target_dir}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Install the latex-unicode package.")
    parser.add_argument(
        "-o",
        "--overwrite",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Overwrite existing files.",
    )
    args = parser.parse_args()
    install(overwrite=args.overwrite)

#!/usr/bin/env python3
"""Import Unicode data: ``python src/import_ucd.py --version 18``.

Versions 17 and 18 have dedicated entry points. Other versions use the current
download layout through ``import_latest``, while still requesting that version.
Only ``latest`` resolves to the most recent release. The license is downloaded
from Unicode's current license URL, independently of the selected data version.
"""

import argparse
import re
from http.client import HTTPException
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlopen

UNICODE_URL = "https://www.unicode.org"
UCD_DIR = Path(__file__).resolve().parents[1] / "third_party" / "ucd"
UCD_FILENAMES = ("Blocks.txt", "ReadMe.txt", "UnicodeData.txt")


def normalize_version(version: str) -> str:
    """Accept latest or a version such as 18, v18, 18.0, or 18.0.0."""
    version = version.strip().lower()
    if version == "latest":
        return version
    match = re.fullmatch(r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?", version)
    if match is None:
        raise ValueError(f"Invalid Unicode version: {version!r}")
    return ".".join(str(int(part or "0")) for part in match.groups())


def download(url: str) -> bytes:
    """Download a file, raising on HTTP errors, timeouts, or empty responses."""
    print(f"Downloading {url}", flush=True)
    with urlopen(url, timeout=30) as response:
        data = response.read()
    if not data:
        raise ValueError(f"Empty response from {url}")
    return data


def read_version(readme: bytes) -> str:
    """Read the release number from either the old or new UCD README format."""
    text = readme.decode("utf-8")
    match = re.search(r"\bversion\s+(\d+\.\d+\.\d+)\b", text, re.IGNORECASE)
    if "Unicode Character Database" not in text or match is None:
        raise ValueError("Cannot determine the Unicode version from ReadMe.txt")
    return match[1]


def validate_files(files: dict[str, bytes], version: str) -> None:
    """Check file formats and release headers before overwriting local data."""
    actual_version = read_version(files["ReadMe.txt"])
    if actual_version != version:
        raise ValueError(f"Requested Unicode {version}, received {actual_version}")

    license_text = files["LICENSE"].decode("utf-8")
    if not license_text.startswith("UNICODE LICENSE V"):
        raise ValueError("The downloaded LICENSE is not a Unicode license")

    blocks = files["Blocks.txt"].decode("utf-8")
    if not blocks.startswith(f"# Blocks-{version}.txt"):
        raise ValueError(f"Blocks.txt does not identify Unicode {version}")
    block_rows = [
        line for line in blocks.splitlines() if line and not line.startswith("#")
    ]
    if not block_rows or any(
        re.fullmatch(r"[0-9A-F]{4,6}\.\.[0-9A-F]{4,6};\s*\S.*", row) is None
        for row in block_rows
    ):
        raise ValueError("Invalid block ranges in Blocks.txt")

    rows = files["UnicodeData.txt"].decode("utf-8").splitlines()
    if not rows:
        raise ValueError("UnicodeData.txt contains no records")
    for number, row in enumerate(rows, start=1):
        fields = row.split(";")
        if len(fields) != 15 or re.fullmatch(r"[0-9A-F]{4,6}", fields[0]) is None:
            raise ValueError(f"Invalid UnicodeData.txt record on line {number}")
        if int(fields[0], 16) > 0x10FFFF:
            raise ValueError(f"Invalid Unicode code point on line {number}")


def import_release(version: str, destination: Path) -> str:
    """Download and validate all four files, then replace the local copies."""
    base_url = f"{UNICODE_URL}/Public/{version}/ucd"
    sources = {
        "LICENSE": f"{UNICODE_URL}/license.txt",
        **{name: f"{base_url}/{name}" for name in UCD_FILENAMES},
    }
    files = {name: download(url) for name, url in sources.items()}
    validate_files(files, version)

    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".ucd-", dir=destination.parent) as staging:
        staging_dir = Path(staging)
        for name, data in files.items():
            (staging_dir / name).write_bytes(data)
        destination.mkdir(exist_ok=True)
        for name in files:
            (staging_dir / name).replace(destination / name)
    print(f"Imported Unicode {version} into {destination}")
    return version


def import_v17(destination: Path = UCD_DIR) -> str:
    """Import the Unicode 17.0.0 release."""
    return import_release("17.0.0", destination)


def import_v18(destination: Path = UCD_DIR) -> str:
    """Import the Unicode 18.0.0 release."""
    return import_release("18.0.0", destination)


def import_latest(version: str = "latest", destination: Path = UCD_DIR) -> str:
    """Use the current download layout for the latest or a specified release."""
    version = normalize_version(version)
    if version == "latest":
        readme = download(f"{UNICODE_URL}/Public/UCD/latest/ucd/ReadMe.txt")
        # Pin the resolved release so a change to latest cannot mix versions.
        version = read_version(readme)
    return import_release(version, destination)


def import_ucd(version: str = "latest", destination: Path = UCD_DIR) -> str:
    """Dispatch known releases and fall back to the generic importer."""
    version = normalize_version(version)
    match version:
        case "17.0.0":
            return import_v17(destination)
        case "18.0.0":
            return import_v18(destination)
        case _:
            return import_latest(version, destination)


def main() -> None:
    """Import a Unicode release selected on the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version",
        default="latest",
        help="Unicode release, e.g. 17, 18.0.0, or latest (default: latest)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=UCD_DIR,
        help="destination directory (default: %(default)s)",
    )
    args = parser.parse_args()
    try:
        import_ucd(args.version, args.output_dir)
    except (OSError, ValueError, HTTPException) as error:
        parser.exit(1, f"error: {error}\n")


if __name__ == "__main__":
    main()

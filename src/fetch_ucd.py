#!/usr/bin/env python3
"""Fetch Unicode data with ``python src/fetch_ucd.py --version 18``.

Download and validate the selected release into third_party/ucd.
Resolve "latest" before downloading release files. Download the license
independently from Unicode's current license URL.
"""

import argparse
import re
import sys
from collections.abc import Sequence
from http.client import HTTPException
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlopen

UNICODE_URL = "https://www.unicode.org"
UCD_DIR = Path(__file__).resolve().parents[1] / "third_party" / "ucd"
UCD_FILENAMES = ("Blocks.txt", "ReadMe.txt", "UnicodeData.txt")
UNICODE_DATA_FIELD_COUNT = 15
MAX_CODE_POINT = 0x10FFFF
DOWNLOAD_TIMEOUT_SECONDS = 30


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
    # Release URLs use the fixed HTTPS Unicode host and validated versions.
    with urlopen(url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:  # noqa: S310
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
    # Confirm the downloaded README identifies the requested release.
    actual_version = read_version(files["ReadMe.txt"])
    if actual_version != version:
        raise ValueError(f"Requested Unicode {version}, received {actual_version}")

    # The current license is independent of the requested Unicode version.
    license_text = files["LICENSE"].decode("utf-8")
    if not license_text.startswith("UNICODE LICENSE V"):
        raise ValueError("The downloaded LICENSE is not a Unicode license")

    # Check the release header and named, inclusive hexadecimal block ranges.
    blocks = files["Blocks.txt"].decode("utf-8")
    if not blocks.startswith(f"# Blocks-{version}.txt"):
        raise ValueError(f"Blocks.txt does not identify Unicode {version}")
    block_rows = [
        line for line in blocks.splitlines() if line and not line.startswith("#")
    ]
    if not block_rows:
        raise ValueError("Blocks.txt contains no block ranges")
    for row in block_rows:
        code_range, name = (field.strip() for field in row.split(";"))
        start, end = (int(bound, 16) for bound in code_range.split(".."))
        if not name or not 0 <= start <= end <= MAX_CODE_POINT:
            raise ValueError("Invalid block range in Blocks.txt")

    # UnicodeData has no release header; check record structure and bounds instead.
    rows = files["UnicodeData.txt"].decode("utf-8").splitlines()
    if not rows:
        raise ValueError("UnicodeData.txt contains no records")
    for number, row in enumerate(rows, start=1):
        fields = row.split(";")
        if len(fields) != UNICODE_DATA_FIELD_COUNT:
            raise ValueError(f"Invalid UnicodeData.txt record on line {number}")
        point = int(fields[0], 16)
        if not 0 <= point <= MAX_CODE_POINT:
            raise ValueError(f"Invalid Unicode code point on line {number}")


def fetch_release(version: str, destination: Path) -> str:
    """Download and validate all four files, then replace the local copies."""
    base_url = f"{UNICODE_URL}/Public/{version}/ucd"
    sources = {
        "LICENSE": f"{UNICODE_URL}/license.txt",
        **{name: f"{base_url}/{name}" for name in UCD_FILENAMES},
    }
    files = {name: download(url) for name, url in sources.items()}
    validate_files(files, version)

    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".ucd-", dir=destination.parent) as staging:
        staging_dir = Path(staging)
        for name, data in files.items():
            (staging_dir / name).write_bytes(data)
        for name in files:
            (staging_dir / name).replace(destination / name)

    print(f"Fetched Unicode {version} into {destination}")
    return version


def fetch_ucd(version: str = "latest", destination: Path = UCD_DIR) -> str:
    """Fetch the requested release, resolving latest to a fixed version first."""
    version = normalize_version(version)
    if version == "latest":
        readme = download(f"{UNICODE_URL}/Public/UCD/latest/ucd/ReadMe.txt")
        # Pin the resolved release so a change to latest cannot mix versions.
        version = read_version(readme)
    return fetch_release(version, destination)


def main(argv: Sequence[str] | None = None) -> int:
    """Fetch a Unicode release selected on the command line."""
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
    args = parser.parse_args(argv)
    try:
        fetch_ucd(args.version, args.output_dir)
    except (OSError, ValueError, HTTPException) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

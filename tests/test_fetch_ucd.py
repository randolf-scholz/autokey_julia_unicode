"""Only HTTP is mocked; validation and file replacement use real data and paths."""

import io
from contextlib import redirect_stderr
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.error import URLError

import pytest
from src import fetch_ucd


def release_files(version: str) -> dict[str, bytes]:
    readme = (
        "This directory contains final data files\n"
        "for the Unicode Character Database, for Version 17.0.0 "
        "of the Unicode Standard.\n"
        if version == "17.0.0"
        else f"This directory contains final data files for version {version} "
        "of the\nUnicode Character Database.\n"
    )
    return {
        "LICENSE": b"UNICODE LICENSE V3\nCopyright Unicode, Inc.\n",
        "Blocks.txt": f"# Blocks-{version}.txt\n0000..007F; Basic Latin\n".encode(),
        "ReadMe.txt": readme.encode(),
        "UnicodeData.txt": b"0041;LATIN CAPITAL LETTER A;Lu;0;L;;;;;N;;;;0061;\n",
    }


def responses(version: str, files: dict[str, bytes]):
    urls = {f"{fetch_ucd.UNICODE_URL}/license.txt": files["LICENSE"]}
    urls.update(
        {
            f"{fetch_ucd.UNICODE_URL}/Public/{version}/ucd/{name}": files[name]
            for name in fetch_ucd.UCD_FILENAMES
        }
    )

    def respond(url: str, **_kwargs) -> io.BytesIO:
        return io.BytesIO(urls[url])

    return respond


@pytest.mark.parametrize(
    ("alias", "version"),
    [
        ("17", "17.0.0"),
        ("v18", "18.0.0"),
        ("18.0", "18.0.0"),
        ("18.0.0", "18.0.0"),
        ("19", "19.0.0"),
    ],
)
def test_selected_release_uses_versioned_urls_and_preserves_bytes(
    alias: str, version: str
) -> None:
    files = release_files(version)
    with (
        TemporaryDirectory() as directory,
        patch.object(fetch_ucd, "urlopen", side_effect=responses(version, files)),
    ):
        assert fetch_ucd.main(["--version", alias, "--output-dir", directory]) == 0
        assert {p.name: p.read_bytes() for p in Path(directory).iterdir()} == files


def test_latest_resolves_once_then_uses_pinned_release_urls() -> None:
    files = release_files("18.0.0")
    respond = responses("18.0.0", files)
    latest = f"{fetch_ucd.UNICODE_URL}/Public/UCD/latest/ucd/ReadMe.txt"

    def download(url: str, *, timeout: int):
        return (
            io.BytesIO(files["ReadMe.txt"])
            if url == latest
            else respond(url, timeout=timeout)
        )

    with (
        TemporaryDirectory() as directory,
        patch.object(fetch_ucd, "urlopen", side_effect=download) as request,
    ):
        assert fetch_ucd.fetch_ucd(destination=Path(directory)) == "18.0.0"
        assert [call.args[0] for call in request.call_args_list].count(latest) == 1


def test_download_failure_preserves_existing_files() -> None:
    old = release_files("17.0.0")
    respond = responses("18.0.0", release_files("18.0.0"))

    def fail_last(url: str, *, timeout: int):
        if url.endswith("UnicodeData.txt"):
            raise URLError("interrupted download")
        return respond(url, timeout=timeout)

    with (
        TemporaryDirectory() as directory,
        redirect_stderr(io.StringIO()) as stderr,
        patch.object(fetch_ucd, "urlopen", side_effect=fail_last),
    ):
        destination = Path(directory)
        for name, data in old.items():
            (destination / name).write_bytes(data)
        assert fetch_ucd.main(["--version", "18", "--output-dir", directory]) == 1
        assert "interrupted download" in stderr.getvalue()
        assert {p.name: p.read_bytes() for p in destination.iterdir()} == old


@pytest.mark.parametrize(
    ("name", "data", "diagnostic"),
    [
        ("LICENSE", b"<html>error</html>", "LICENSE"),
        ("Blocks.txt", release_files("17.0.0")["Blocks.txt"], "Blocks"),
        ("ReadMe.txt", release_files("17.0.0")["ReadMe.txt"], "Requested Unicode"),
        ("UnicodeData.txt", b"bad;record", "Invalid UnicodeData"),
        ("UnicodeData.txt", b"", "Empty response"),
        (
            "Blocks.txt",
            b"# Blocks-18.0.0.txt\n007F..0000; Reversed\n",
            "Invalid block range",
        ),
        (
            "UnicodeData.txt",
            b"110000;OUT OF RANGE;Lu;0;L;;;;;N;;;;;\n",
            "Invalid Unicode code point",
        ),
    ],
)
def test_invalid_downloads_preserve_existing_release(
    name: str, data: bytes, diagnostic: str
) -> None:
    with TemporaryDirectory() as directory:
        destination = Path(directory)
        old = release_files("17.0.0")
        for filename, contents in old.items():
            (destination / filename).write_bytes(contents)
        files = release_files("18.0.0") | {name: data}
        with (
            patch.object(fetch_ucd, "urlopen", side_effect=responses("18.0.0", files)),
            pytest.raises(ValueError, match=diagnostic),
        ):
            fetch_ucd.fetch_ucd("18", destination)
        assert {p.name: p.read_bytes() for p in destination.iterdir()} == old


@pytest.mark.parametrize("version", ["invalid", "18.0.0.1", "../latest", ""])
def test_invalid_versions_make_no_network_requests(version: str) -> None:
    with (
        TemporaryDirectory() as directory,
        patch.object(fetch_ucd, "urlopen") as request,
    ):
        with pytest.raises(ValueError, match="Invalid Unicode version"):
            fetch_ucd.fetch_ucd(version, Path(directory))
        request.assert_not_called()

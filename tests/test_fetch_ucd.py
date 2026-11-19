"""Mock download for fetching tests; exercise the helper with local files."""

import io
from collections.abc import Callable
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
        "NameAliases.txt": (
            f"# NameAliases-{version}.txt\n007F;DELETE;control\n"
        ).encode(),
    }


def responses(version: str, files: dict[str, bytes]) -> Callable[..., bytes]:
    content = {
        f"{fetch_ucd.UNICODE_URL}/license.txt": files["LICENSE"],
        **{
            f"{fetch_ucd.UNICODE_URL}/Public/{version}/ucd/{name}": files[name]
            for name in fetch_ucd.UCD_FILENAMES
        },
    }
    return lambda url, **_kwargs: content[url]


def test_download_reads_local_file(tmp_path: Path) -> None:
    source = tmp_path / "response.txt"
    data = b"Unicode data\n\x00\xff"
    source.write_bytes(data)
    assert fetch_ucd.download(source.as_uri(), timeout=5, data=None) == data


def test_download_rejects_empty_response(tmp_path: Path) -> None:
    source = tmp_path / "empty.txt"
    source.write_bytes(b"")
    with pytest.raises(ValueError, match="Empty response"):
        fetch_ucd.download(source.as_uri(), timeout=5)


@pytest.mark.parametrize(
    ("alias", "version"),
    [
        ("17", "17.0.0"),
        ("v18", "18.0.0"),
        ("18.0", "18.0.0"),
        ("18.0.0", "18.0.0"),
    ],
)
def test_selected_release_uses_versioned_urls_and_preserves_bytes(
    alias: str, version: str
) -> None:
    files = release_files(version)
    with (
        TemporaryDirectory() as directory,
        patch.object(fetch_ucd, "download", side_effect=responses(version, files)),
    ):
        assert fetch_ucd.main(["--version", alias, "--output-dir", directory]) == 0
        assert {p.name: p.read_bytes() for p in Path(directory).iterdir()} == files


@pytest.mark.parametrize("timeout", [5.0, None])
def test_latest_resolves_once_and_forwards_options_to_pinned_downloads(
    timeout: float | None,
) -> None:
    files = release_files("18.0.0")
    respond = responses("18.0.0", files)
    latest = f"{fetch_ucd.UNICODE_URL}/Public/UCD/latest/ucd/ReadMe.txt"
    context = object()

    def respond_request(url: str, **kwargs: object) -> bytes:
        if url == latest:
            return files["ReadMe.txt"]
        return respond(url, **kwargs)

    with (
        TemporaryDirectory() as directory,
        patch.object(fetch_ucd, "download", side_effect=respond_request) as request,
    ):
        actual_version = fetch_ucd.fetch_release(
            "latest", destination=Path(directory), timeout=timeout, context=context
        )
        assert actual_version == "18.0.0"
        assert request.call_count == 6
        assert [call.args[0] for call in request.call_args_list].count(latest) == 1
        assert all(
            call.kwargs == {"timeout": timeout, "context": context}
            for call in request.call_args_list
        )
        assert {p.name: p.read_bytes() for p in Path(directory).iterdir()} == files


def test_empty_latest_response_does_not_create_destination() -> None:
    with (
        TemporaryDirectory() as directory,
        patch.object(
            fetch_ucd, "download", side_effect=ValueError("Empty response")
        ) as request,
    ):
        destination = Path(directory) / "ucd"
        with pytest.raises(ValueError, match="Empty response"):
            fetch_ucd.fetch_release("latest", destination=destination)
        request.assert_called_once()
        assert not destination.exists()


@pytest.mark.parametrize(
    "error", [URLError("interrupted download"), ValueError("Empty response")]
)
@pytest.mark.parametrize("failed_file", ["UnicodeData.txt", "NameAliases.txt"])
def test_download_failure_preserves_existing_files(
    error: Exception, failed_file: str
) -> None:
    old = release_files("17.0.0")
    respond = responses("18.0.0", release_files("18.0.0"))

    def fail_last(url: str, **kwargs: object) -> bytes:
        if url.endswith(failed_file):
            raise error
        return respond(url, **kwargs)

    with (
        TemporaryDirectory() as directory,
        redirect_stderr(io.StringIO()) as stderr,
        patch.object(fetch_ucd, "download", side_effect=fail_last),
    ):
        destination = Path(directory)
        for name, data in old.items():
            (destination / name).write_bytes(data)
        assert fetch_ucd.main(["--version", "18", "--output-dir", directory]) == 1
        assert str(error) in stderr.getvalue()
        assert {p.name: p.read_bytes() for p in destination.iterdir()} == old


@pytest.mark.parametrize(
    ("name", "data", "diagnostic"),
    [
        ("LICENSE", b"<html>error</html>", "LICENSE"),
        ("Blocks.txt", release_files("17.0.0")["Blocks.txt"], "Blocks"),
        ("ReadMe.txt", release_files("17.0.0")["ReadMe.txt"], "Requested Unicode"),
        ("UnicodeData.txt", b"bad;record", "Invalid UnicodeData"),
        ("NameAliases.txt", release_files("17.0.0")["NameAliases.txt"], "NameAliases"),
        ("NameAliases.txt", b"# NameAliases-18.0.0.txt\n", "no aliases"),
        (
            "NameAliases.txt",
            b"# NameAliases-18.0.0.txt\nbad;record\n",
            "Invalid NameAliases",
        ),
        (
            "NameAliases.txt",
            b"# NameAliases-18.0.0.txt\n110000;NAME;control\n",
            "code point",
        ),
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
def test_validate_files_rejects_invalid_data(
    name: str, data: bytes, diagnostic: str
) -> None:
    files = release_files("18.0.0") | {name: data}
    with pytest.raises(ValueError, match=diagnostic):
        fetch_ucd.validate_files(files, "18.0.0")


def test_validation_failure_preserves_existing_release() -> None:
    with TemporaryDirectory() as directory:
        destination = Path(directory)
        old = release_files("17.0.0")
        for filename, contents in old.items():
            (destination / filename).write_bytes(contents)
        files = release_files("18.0.0") | {"LICENSE": b"<html>error</html>"}
        with (
            patch.object(fetch_ucd, "download", side_effect=responses("18.0.0", files)),
            pytest.raises(ValueError, match="LICENSE"),
        ):
            fetch_ucd.fetch_release("18", destination)
        assert {p.name: p.read_bytes() for p in destination.iterdir()} == old


@pytest.mark.parametrize("version", ["invalid", "18.0.0.1", "../latest", ""])
def test_invalid_versions_make_no_network_requests(version: str) -> None:
    with (
        TemporaryDirectory() as directory,
        patch.object(fetch_ucd, "download") as request,
    ):
        with pytest.raises(ValueError, match="Invalid Unicode version"):
            fetch_ucd.fetch_release(version, Path(directory))
        request.assert_not_called()

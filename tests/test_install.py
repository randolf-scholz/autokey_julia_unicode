"""Exercise generated files and installation transactions on temporary directories."""

import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Literal

import pytest
from src import install_autokey as install

ROOT = Path(__file__).resolve().parents[1]
ICONS_FILENAME = "icons-julia.tsv"
HEADER = "code_points\tchars\ttab_completions\tunicode_name\n"


def write_icons(path: Path, rows: str = "U+0041\tA\t\\A\tLetter A\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(HEADER + rows, encoding="utf8")
    return path


def snapshot(root: Path) -> dict[Path, bytes]:
    return {
        path.relative_to(root): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and path.name != install.LOG_FILENAME
    }


@pytest.fixture
def assets(tmp_path: Path) -> Path:
    return Path(shutil.copytree(install.ASSETS_DIR, tmp_path / "assets"))


@pytest.fixture
def build(tmp_path: Path, assets: Path) -> Path:
    source = write_icons(tmp_path / "letters" / ICONS_FILENAME).parent
    directory = tmp_path / "build"
    install.build_assets(
        [source],
        send_mode=install.SendMode.CTRL_SHIFT_V,
        duplicates="skip",
        build_dir=directory,
        assets_dir=assets,
    )
    return directory


def run_install(build: Path, target: Path, answers: str) -> subprocess.CompletedProcess:
    """Supply real stdin to the installer without a running AutoKey instance."""
    return subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys
from pathlib import Path
from src.install_autokey import install_build, installation_logging
with installation_logging(Path(sys.argv[2]), verbose=False):
    install_build(Path(sys.argv[1]), build_dir=Path(sys.argv[2]))
""",
            str(target),
            str(build),
        ],
        cwd=ROOT,
        input=answers,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )


def test_build_contains_all_asset_types_and_autokey_096_metadata(build: Path):
    assert {path.name for path in build.iterdir()} == {
        "letters",
        "latex_snippets",
        "special_chars",
        "custom_scripts",
    }
    assert (build / "letters/U+0041.txt").read_bytes() == b"A"
    metadata = json.loads((build / "letters/U+0041.json").read_text())
    assert metadata["abbreviation"]["abbreviations"] == ["\\A "]
    assert metadata["sendMode"] == "<ctrl>+<shift>+v"
    assert metadata["description"] == "Letter A"
    assert not list(build.rglob(".*.json"))
    assert not list(build.rglob("*.toml"))
    for name, payload in (("newline", b"\n"), ("tabulator", b"\t")):
        assert (build / "special_chars" / f"{name}.txt").read_bytes() == payload
    for name in ("help", "subscripts"):
        assert (build / "custom_scripts" / f"{name}.py").read_bytes() == (
            install.ASSETS_DIR / "custom_scripts" / f"{name}.py"
        ).read_bytes()
        metadata = json.loads((build / "custom_scripts" / f"{name}.json").read_text())
        config = tomllib.loads(
            (install.ASSETS_DIR / "custom_scripts" / f"{name}.toml").read_text()
        )
        assert metadata["type"] == "script"
        assert metadata["description"] == config["description"]
        assert (
            metadata["abbreviation"]["abbreviations"]
            == config["abbreviation"]["abbreviations"]
        )
    for source in (install.ASSETS_DIR / "latex_snippets").glob("*.toml"):
        config = tomllib.loads(source.read_text())
        assert (
            build / "latex_snippets" / source.with_suffix(".txt").name
        ).read_bytes() == config["payload"].encode()
        metadata = json.loads(
            (build / "latex_snippets" / source.with_suffix(".json").name).read_text()
        )
        assert (
            metadata["abbreviation"]["abbreviations"]
            == config["abbreviation"]["abbreviations"]
        )


def test_phrase_overrides_merge_with_defaults_and_preserve_payload(
    tmp_path: Path, assets: Path
):
    source = assets / "latex_snippets"
    shutil.rmtree(source)
    source.mkdir()
    (source / "custom.toml").write_text("""
    description = "Custom snippet"
    payload = "first\\nsecond\\n"
    abbreviation.abbreviations = ["!custom"]
    abbreviation.immediate = false
    filter.regex = "Custom app"
    """)
    install.build_phrases(
        source, send_mode=install.SendMode.SHIFT_INSERT, build_dir=tmp_path
    )
    result = tmp_path / "latex_snippets"
    assert (result / "custom.txt").read_bytes() == b"first\nsecond\n"
    metadata = json.loads((result / "custom.json").read_text())
    assert metadata["description"] == "Custom snippet"
    assert metadata["sendMode"] == "<shift>+<insert>"
    assert metadata["abbreviation"]["abbreviations"] == ["!custom"]
    assert metadata["abbreviation"]["immediate"] is False
    assert metadata["abbreviation"]["backspace"] is True
    assert metadata["filter"] == {"regex": "Custom app", "isRecursive": False}
    assert "payload" not in metadata


@pytest.mark.parametrize(
    "contents, field",
    [
        ('payload = 42\nabbreviation.abbreviations = ["!eq"]', "payload"),
        ('payload = "text"\nabbreviation = "!eq"', "abbreviation"),
        (
            'payload = "text"\nabbreviation.abbreviations = "!eq"',
            "abbreviation.abbreviations",
        ),
        (
            'payload = "text"\nabbreviation.abbreviations = [1]',
            "abbreviation.abbreviations",
        ),
        ('payload = "text"', "abbreviation.abbreviations"),
        (
            'payload = "text"\ndescription = false\nabbreviation.abbreviations = ["!eq"]',
            "description",
        ),
    ],
)
def test_invalid_phrase_metadata_reports_source(
    tmp_path: Path, assets: Path, contents: str, field: str
):
    source = assets / "phrases"
    source.mkdir()
    config = source / "bad.toml"
    config.write_text(contents)
    with pytest.raises(TypeError) as error:
        install.build_phrases(
            source, send_mode=install.SendMode.CTRL_V, build_dir=tmp_path
        )
    assert str(config) in str(error.value)
    assert field in str(error.value)


def test_missing_script_is_rejected(tmp_path: Path, assets: Path):
    (assets / "custom_scripts/help.py").unlink()
    with pytest.raises(FileNotFoundError, match="Missing Python script"):
        install.build_custom_scripts(assets / "custom_scripts", build_dir=tmp_path)


def test_script_metadata_requires_description(tmp_path: Path, assets: Path):
    (assets / "custom_scripts/help.toml").write_text(
        "abbreviation.abbreviations = ['help']"
    )
    with pytest.raises(TypeError, match="description"):
        install.build_custom_scripts(assets / "custom_scripts", build_dir=tmp_path)


@pytest.mark.parametrize(
    "rows, expected",
    [
        ("U+00041\tA\t\\A\tLetter A\n", {"U+0041.txt": b"A"}),
        (
            "U+2705, U+FE0F\t\t\\check\tCheck mark\n",
            {"U+2705_U+FE0F.txt": "✅️".encode()},
        ),
        ("U+0301\t́\t\\acute\tCombining acute\n", {"U+0301.txt": "́".encode()}),
        ("U+0009\t\t\\t\t\n", {"U+0009.txt": b"\t"}),
        ("U+0041, U+0042\tAB\t\\AB\tPhrase\nU+0042\tB\t\tNo alias\n", {}),
    ],
)
def test_icon_processing_builds_supported_replacements(
    tmp_path: Path, assets: Path, rows: str, expected: dict
):
    source = write_icons(tmp_path / "icons" / ICONS_FILENAME, rows).parent
    output = tmp_path / "build"
    install.build_assets(
        [source],
        send_mode=install.SendMode.CTRL_V,
        duplicates="skip",
        build_dir=output,
        assets_dir=assets,
    )
    assert {
        p.name: p.read_bytes() for p in (output / "icons").glob("*.txt")
    } == expected


@pytest.mark.parametrize(
    "row",
    [
        "U+0042\tA\t\\A\tMismatch\n",
        "U+D800\t\t\\A\tSurrogate\n",
        "U+110000\t\t\\A\tOut of range\n",
        "U+0041 + U+0042\tA\t\\A\tOld format\n",
    ],
)
def test_invalid_icon_codes_and_mismatches_are_rejected(tmp_path: Path, row: str):
    path = write_icons(tmp_path / ICONS_FILENAME, row)
    with pytest.raises(ValueError):
        install.process_icons(path)


def test_icon_reader_accepts_reordered_columns_and_literal_quotes(tmp_path: Path):
    path = tmp_path / ICONS_FILENAME
    path.write_text(
        "notes\tunicode_name\ttab_completions\tchars\tcode_points\n"
        'ignored\tQUOTATION MARK\t\\quote\t"\tU+0022\n'
    )
    (sample,) = install.process_icons(path).samples
    assert sample.glyph == '"'
    assert sample.abbreviations == ["\\quote "]


@pytest.mark.parametrize(
    "text, diagnostic",
    [
        ("", "Missing columns"),
        (
            "Code point(s)\tCharacter(s)\tTab completion sequence(s)\tUnicode name(s)\n",
            "Missing columns",
        ),
        (HEADER + "U+0041\tA\t\\A\n", "Missing values"),
    ],
)
def test_malformed_icon_file_reports_path(tmp_path: Path, text: str, diagnostic: str):
    path = tmp_path / ICONS_FILENAME
    path.write_text(text)
    with pytest.raises(ValueError, match=diagnostic) as error:
        list(install.load_icons(path))
    assert str(path) in str(error.value)


@pytest.mark.parametrize("policy", ["skip", "error"])
def test_duplicate_policy(
    tmp_path: Path, assets: Path, policy: Literal["skip", "error"]
):
    source = write_icons(
        tmp_path / "letters/a-first.tsv", "U+0041\tA\t\\first\tLetter A\n"
    ).parent
    write_icons(source / "z-last.tsv")
    output = tmp_path / "build"
    if policy == "error":
        with pytest.raises(FileExistsError):
            install.build_assets(
                [source],
                send_mode=install.SendMode.CTRL_V,
                duplicates=policy,
                build_dir=output,
                assets_dir=assets,
            )
    else:
        install.build_assets(
            [source],
            send_mode=install.SendMode.CTRL_V,
            duplicates=policy,
            build_dir=output,
            assets_dir=assets,
        )
        metadata = json.loads((output / "letters/U+0041.json").read_text())
        assert metadata["abbreviation"]["abbreviations"] == ["\\first "]


def test_colliding_collection_names_are_rejected(tmp_path: Path, assets: Path):
    first = write_icons(tmp_path / "one/letters" / ICONS_FILENAME).parent
    second = write_icons(tmp_path / "two/letters" / ICONS_FILENAME).parent
    with pytest.raises(FileExistsError):
        install.build_assets(
            [first, second],
            send_mode=install.SendMode.CTRL_V,
            duplicates="skip",
            build_dir=tmp_path / "build",
            assets_dir=assets,
        )


@pytest.mark.parametrize(
    "answers, selected",
    [("0\n1\n", {"tabulator"}), ("\n\n", set()), ("1\n1\n", {"newline", "tabulator"})],
)
def test_install_selects_special_characters_and_retains_independent_build(
    build: Path, tmp_path: Path, answers: str, selected: set
):
    target = tmp_path / "installed"
    before = snapshot(build)
    (build / install.LOG_FILENAME).write_text("build log")
    result = run_install(build, target, answers)
    assert result.returncode == 0, result.stderr
    assert {p.stem for p in (target / "special_chars").glob("*.txt")} == selected
    expected = {
        path: data
        for path, data in before.items()
        if path.parts[0] != "special_chars" or path.stem in selected
    }
    assert snapshot(target) == expected
    assert not (target / install.LOG_FILENAME).exists()
    (target / "letters/U+0041.txt").write_bytes(b"edited")
    assert snapshot(build) == before


def test_reinstall_replaces_entire_target_but_preserves_siblings(
    build: Path, tmp_path: Path
):
    target = tmp_path / "installed"
    target.mkdir()
    (target / "obsolete.txt").write_text("obsolete")
    sibling = tmp_path / "personal.txt"
    sibling.write_text("keep")
    result = run_install(build, target, "invalid\n9\n1\n1\n1\n")
    assert result.returncode == 0, result.stderr
    assert snapshot(target) == snapshot(build)
    assert sibling.read_text() == "keep"
    assert not list(tmp_path.glob(".installed-*"))


@pytest.mark.parametrize("answers", ["\n", "1\n0\n"])
def test_declining_or_interrupting_prompts_preserves_target_and_build(
    build: Path, tmp_path: Path, answers: str
):
    target = tmp_path / "installed"
    target.mkdir()
    (target / "keep.txt").write_text("keep")
    before = snapshot(build)
    result = run_install(build, target, answers)
    assert result.returncode == (0 if answers == "\n" else 1)
    assert snapshot(target) == {Path("keep.txt"): b"keep"}
    assert snapshot(build) == before


@pytest.mark.parametrize("dangling", [False, True])
def test_replacing_target_symlink_preserves_external_files(
    build: Path, tmp_path: Path, dangling: bool
):
    external = tmp_path / "external"
    external.mkdir()
    (external / "keep.txt").write_text("keep")
    target = tmp_path / "installed"
    target.symlink_to(
        tmp_path / "missing" if dangling else external, target_is_directory=True
    )
    result = run_install(build, target, "1\n1\n1\n")
    assert result.returncode == 0, result.stderr
    assert not target.is_symlink()
    assert snapshot(target) == snapshot(build)
    assert (external / "keep.txt").read_text() == "keep"


def test_build_cleanup_unlinks_children_and_rejects_symlink_root(tmp_path: Path):
    external = tmp_path / "external"
    external.mkdir()
    (external / "keep.txt").write_text("keep")
    build = tmp_path / "build"
    build.mkdir()
    (build / "stale").symlink_to(external, target_is_directory=True)
    (build / install.LOG_FILENAME).write_text("log")
    install.clear_build_assets(build)
    assert {p.name for p in build.iterdir()} == {install.LOG_FILENAME}
    assert (external / "keep.txt").read_text() == "keep"
    alias = tmp_path / "build-link"
    alias.symlink_to(external, target_is_directory=True)
    with pytest.raises(OSError, match="symlink"):
        install.clear_build_assets(alias)
    assert (external / "keep.txt").read_text() == "keep"


@pytest.mark.parametrize(
    "target", ["build", "build/installed", ".", "autokey/data", "autokey"]
)
def test_unsafe_targets_are_rejected(tmp_path: Path, target: str):
    with pytest.raises(ValueError):
        install.validate_install_target(
            tmp_path / target,
            build_dir=tmp_path / "build",
            autokey_dir=tmp_path / "autokey/data",
        )


def test_target_checks_resolve_symlink_aliases(tmp_path: Path):
    build = tmp_path / "build"
    build.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(build, target_is_directory=True)
    with pytest.raises(ValueError, match="outside"):
        install.validate_install_target(
            alias / "installed", build_dir=build, autokey_dir=tmp_path / "autokey/data"
        )


@pytest.fixture
def installer(tmp_path: Path, assets: Path) -> Path:
    source = tmp_path / "project/src"
    source.mkdir(parents=True)
    script = Path(shutil.copy2(install.__file__, source / "install_autokey.py"))
    shutil.copytree(assets, source.parent / "data/autokey")
    return script


@pytest.mark.parametrize(
    "flag, verbose", [("--build-only", False), ("--dry-run", True)]
)
def test_build_only_cli_needs_no_autokey_or_input(
    installer: Path, tmp_path: Path, flag: str, verbose: bool
):
    source = write_icons(tmp_path / "letters" / ICONS_FILENAME).parent
    result = subprocess.run(
        [
            sys.executable,
            str(installer),
            flag,
            *(["--verbose"] if verbose else []),
            str(source),
        ],
        cwd=tmp_path,
        env=os.environ | {"HOME": str(tmp_path / "home")},
        input="",
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    build = installer.parents[1] / "build/autokey"
    assert (build / "letters/U+0041.txt").read_bytes() == b"A"
    metadata = json.loads((build / "letters/U+0041.json").read_text())
    assert metadata["sendMode"] == "<ctrl>+v"
    assert not (tmp_path / "home/.config").exists()
    log = (build / install.LOG_FILENAME).read_text()
    assert "Registered" in log and "Build complete" in log
    assert "\033[" not in log + result.stderr
    assert ("DEBUG:" in result.stderr) == verbose


def test_missing_default_autokey_directory_fails_before_build(
    installer: Path, tmp_path: Path
):
    result = subprocess.run(
        [sys.executable, str(installer)],
        env=os.environ | {"HOME": str(tmp_path / "home")},
        input="",
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 2
    assert "--autokey-directory" in result.stderr
    assert not (installer.parents[1] / "build").exists()


def test_default_sources_build_flat_icons_collection(installer: Path, tmp_path: Path):
    project = installer.parents[1]
    icons = write_icons(project / "data/icons" / ICONS_FILENAME).parent
    write_icons(icons / "custom_unicode/custom.tsv", "U+0042\tB\t\\B\tLetter B\n")
    ucd = project / "data/ucd"
    ucd.mkdir()
    (ucd / "blocks.tsv").write_text(
        "block_start\tblock_end\tblock_name\n0000\t007F\tBasic Latin\n"
    )
    (ucd / "unicode.tsv").write_text(HEADER + "U+0041\tA\t\tLetter A\n")
    result = subprocess.run(
        [sys.executable, str(installer), "--build-only"],
        cwd=project,
        env=os.environ | {"HOME": str(tmp_path / "home")},
        input="",
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    build = project / "build/autokey"
    assert (build / "icons/U+0041.txt").read_bytes() == b"A"
    assert (build / "custom_unicode/U+0042.txt").read_bytes() == b"B"
    assert not (build / "julia_unicode").exists()
    assert "blocks.tsv" not in result.stderr
    assert "unicode.tsv" not in result.stderr


def test_late_build_error_preserves_installation_and_logs_failure(
    tmp_path: Path, installer: Path
):
    source = write_icons(tmp_path / "letters" / ICONS_FILENAME).parent
    target = tmp_path / "installed"
    target.mkdir()
    (target / "keep.txt").write_text("keep")
    (installer.parents[1] / "data/autokey/latex_snippets/align.toml").write_text(
        "not valid TOML ="
    )
    result = subprocess.run(
        [
            sys.executable,
            str(installer),
            "--autokey-directory",
            str(target),
            "--sendmode",
            "0",
            str(source),
        ],
        input="",
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode != 0
    assert "Replace the entire" not in result.stdout
    build = installer.parents[1] / "build/autokey"
    assert snapshot(target) == {Path("keep.txt"): b"keep"}
    assert (build / "letters/U+0041.txt").read_bytes() == b"A"
    assert "Traceback" in (build / install.LOG_FILENAME).read_text()


def write_frontend(directory: Path, name: str, body: str):
    path = directory / name
    path.write_text("#!/bin/sh\n" + body + "\n")
    path.chmod(0o755)


@pytest.mark.parametrize("version", ["0.96.0", "0.100.0", "1.0.0", "0.95.10"])
def test_system_version_check_runs_frontend(tmp_path: Path, version: str):
    write_frontend(tmp_path, "autokey-gtk", f"echo 'autokey-gtk Version {version}'")
    if version == "0.95.10":
        with pytest.raises(SystemExit, match="found 0.95.10"):
            install.check_autokey_version(str(tmp_path))
    else:
        install.check_autokey_version(str(tmp_path))


def test_version_check_uses_qt_if_gtk_fails(tmp_path: Path):
    write_frontend(tmp_path, "autokey-gtk", "exit 1")
    write_frontend(tmp_path, "autokey-qt", "echo 'autokey-qt Version 0.95.10'")
    with pytest.raises(SystemExit, match="found 0.95.10"):
        install.check_autokey_version(str(tmp_path))


@pytest.mark.parametrize("body", [None, "echo 'unknown version'", "exit 1"])
def test_missing_or_unreadable_version_warns_and_continues(
    tmp_path: Path, caplog, body: str | None
):
    if body is not None:
        write_frontend(tmp_path, "autokey-gtk", body)
    install.check_autokey_version(str(tmp_path))
    assert "Could not determine" in caplog.text

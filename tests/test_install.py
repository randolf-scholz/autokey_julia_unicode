"""Exercise generated files and installation transactions on temporary directories."""

import json
import shutil
import tomllib
from collections.abc import Iterator
from contextlib import chdir, contextmanager, redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Literal
from unittest.mock import patch

import pytest
from src import install_autokey as install

ICONS_DIR = Path("icons")
JULIA_ICONS = ICONS_DIR / "julia"
CUSTOM_ICONS = ICONS_DIR / "custom"
LATEX_SNIPPETS = Path("latex_snippets")
CUSTOM_SCRIPTS = Path("custom_scripts")
SPECIAL_CHARS = Path("special_chars")
SCRIPT_FILE = CUSTOM_SCRIPTS / "example.py"
SCRIPT_METADATA = CUSTOM_SCRIPTS / "example.toml"
SNIPPET_FILE = LATEX_SNIPPETS / "example.toml"
SCRIPT_CONTENT = b"print('synthetic script')\n"
EXTENSION_NAME = install.DEFAULT_TARGET_DIR.name
ICONS_FILENAME = "sample.tsv"
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


def write_assets(directory: Path) -> Path:
    """Write synthetic templates, snippets, and scripts for the installer."""
    for collection in ("templates", LATEX_SNIPPETS, CUSTOM_SCRIPTS, SPECIAL_CHARS):
        (directory / collection).mkdir(parents=True)
    for name, kind in (("phrase", "phrase"), ("script", "script")):
        template = {
            "type": kind,
            "description": None,
            "sendMode": None,
            "abbreviation": {
                "abbreviations": None,
                "immediate": True,
                "backspace": True,
            },
            "filter": {"regex": None, "isRecursive": False},
        }
        (directory / "templates" / f"{name}.json").write_text(json.dumps(template))
    (directory / SNIPPET_FILE).write_text(
        'payload = "synthetic snippet\\n"\nabbreviation.abbreviations = ["!snippet"]\n'
    )
    for name, payload in (("newline", "\n"), ("tabulator", "\t")):
        (directory / SPECIAL_CHARS / f"{name}.toml").write_text(
            f"payload = {json.dumps(payload)}\n"
            f'abbreviation.abbreviations = ["!{name}"]\n'
        )
    (directory / SCRIPT_FILE).write_bytes(SCRIPT_CONTENT)
    (directory / SCRIPT_METADATA).write_text(
        'description = "Synthetic script"\n'
        'abbreviation.abbreviations = ["!script"]\n'
        'filter.regex = "Script app"\n'
    )
    return directory


@contextmanager
def temporary_project() -> Iterator[Path]:
    """Keep installer paths and generated assets inside a temporary directory."""
    with TemporaryDirectory() as tmpdir:
        directory = Path(tmpdir)
        project = directory / "project"
        autokey = directory / "autokey"
        with (
            patch.multiple(
                install,
                PROJECT_DIR=project,
                DATA_DIR=project / "tables",
                ASSETS_DIR=write_assets(directory / "assets"),
                BUILD_DIR=project / "generated",
                AUTOKEY_DIR=autokey,
                DEFAULT_TARGET_DIR=autokey / EXTENSION_NAME,
            ),
            patch.object(install.shutil, "which", return_value=None),
        ):
            yield directory


def build_project() -> Path:
    """Build the default icon collection and synthetic assets."""
    write_icons(install.DATA_DIR / ICONS_DIR / "letters" / ICONS_FILENAME)
    assert install.main(["--build-only", "--sendmode", "1"]) == 0
    return install.BUILD_DIR


def run_install(target: Path, answers: str, monkeypatch: pytest.MonkeyPatch) -> int:
    """Run the CLI in process with a finite stream of prompt answers."""
    responses = iter(answers.splitlines())

    def respond(_prompt: str) -> str:
        try:
            return next(responses)
        except StopIteration:
            raise EOFError("No more test input") from None

    monkeypatch.setattr("builtins.input", respond)
    return install.main(["--autokey-directory", str(target), "--sendmode", "1"])


def test_phrase_overrides_merge_with_defaults_and_preserve_payload() -> None:
    with temporary_project() as directory:
        assets = install.ASSETS_DIR
        source = assets / LATEX_SNIPPETS.name
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
            source, send_mode=install.SendMode.SHIFT_INSERT, build_dir=directory
        )
        result = directory / LATEX_SNIPPETS.name
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
    ("contents", "field"),
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
            (
                'payload = "text"\ndescription = false\n'
                'abbreviation.abbreviations = ["!eq"]'
            ),
            "description",
        ),
    ],
)
def test_invalid_phrase_metadata_reports_source(contents: str, field: str) -> None:
    with temporary_project() as directory:
        assets = install.ASSETS_DIR
        source = assets / "phrases"
        source.mkdir()
        config = source / "bad.toml"
        config.write_text(contents)
        with pytest.raises(TypeError) as error:
            install.build_phrases(
                source, send_mode=install.SendMode.CTRL_V, build_dir=directory
            )
        assert str(config) in str(error.value)
        assert field in str(error.value)


def test_script_payload_is_copied_and_metadata_is_merged() -> None:
    with temporary_project():
        build = build_project()
        assert (build / SCRIPT_FILE).read_bytes() == SCRIPT_CONTENT
        metadata = json.loads((build / SCRIPT_FILE.with_suffix(".json")).read_text())
        assert metadata["type"] == "script"
        assert metadata["description"] == "Synthetic script"
        assert metadata["abbreviation"]["abbreviations"] == ["!script"]
        assert metadata["abbreviation"]["backspace"] is True
        assert metadata["filter"] == {"regex": "Script app", "isRecursive": False}


def test_script_metadata_requires_description() -> None:
    with temporary_project() as directory:
        assets = install.ASSETS_DIR
        (assets / SCRIPT_METADATA).write_text(
            "abbreviation.abbreviations = ['!script']"
        )
        with pytest.raises(TypeError, match="description"):
            install.build_custom_scripts(
                assets / CUSTOM_SCRIPTS.name, build_dir=directory
            )


@pytest.mark.parametrize(
    ("rows", "expected"),
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
    rows: str, expected: dict
) -> None:
    with temporary_project() as directory:
        assets = install.ASSETS_DIR
        source = write_icons(directory / "icons" / ICONS_FILENAME, rows).parent
        output = directory / "build"
        install.build_assets(
            [source],
            send_mode=install.SendMode.CTRL_V,
            duplicates="skip",
            build_dir=output,
            assets_dir=assets,
        )
        actual = {p.name: p.read_bytes() for p in (output / "icons").glob("*.txt")}
        assert actual == expected


@pytest.mark.parametrize(
    ("row", "diagnostic"),
    [
        ("U+0042\tA\t\\A\tMismatch\n", "Mismatch"),
        ("U+D800\t\t\\A\tSurrogate\n", "Unicode scalar value"),
        ("U+110000\t\t\\A\tOut of range\n", "Unicode scalar value"),
        ("U+0041 + U+0042\tA\t\\A\tOld format\n", "valid unicode code"),
    ],
)
def test_invalid_icon_codes_and_mismatches_are_rejected(
    row: str, diagnostic: str
) -> None:
    with TemporaryDirectory() as tmpdir:
        directory = Path(tmpdir)
        path = write_icons(directory / ICONS_FILENAME, row)
        with pytest.raises(ValueError, match=diagnostic):
            install.process_icons(path)


def test_icon_reader_accepts_reordered_columns_and_literal_quotes() -> None:
    with TemporaryDirectory() as tmpdir:
        directory = Path(tmpdir)
        path = directory / ICONS_FILENAME
        path.write_text(
            "notes\tunicode_name\ttab_completions\tchars\tcode_points\n"
            'ignored\tQUOTATION MARK\t\\quote\t"\tU+0022\n'
        )
        (sample,) = install.process_icons(path).samples
        assert sample.glyph == '"'
        assert sample.abbreviations == ["\\quote "]


@pytest.mark.parametrize(
    ("text", "diagnostic"),
    [
        ("", "Missing columns"),
        (
            (
                "Code point(s)\tCharacter(s)\tTab completion sequence(s)\t"
                "Unicode name(s)\n"
            ),
            "Missing columns",
        ),
        (HEADER + "U+0041\tA\t\\A\n", "Missing values"),
    ],
)
def test_malformed_icon_file_reports_path(text: str, diagnostic: str) -> None:
    with TemporaryDirectory() as tmpdir:
        directory = Path(tmpdir)
        path = directory / ICONS_FILENAME
        path.write_text(text)
        with pytest.raises(ValueError, match=diagnostic) as error:
            list(install.load_icons(path))
        assert str(path) in str(error.value)


@pytest.mark.parametrize("policy", ["skip", "error"])
def test_duplicate_policy(policy: Literal["skip", "error"]) -> None:
    with temporary_project() as directory:
        assets = install.ASSETS_DIR
        source = write_icons(
            directory / "letters/a-first.tsv", "U+0041\tA\t\\first\tLetter A\n"
        ).parent
        write_icons(source / "z-last.tsv")
        output = directory / "build"
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


def test_colliding_collection_names_are_rejected() -> None:
    with temporary_project() as directory:
        assets = install.ASSETS_DIR
        first = write_icons(directory / "one/letters" / ICONS_FILENAME).parent
        second = write_icons(directory / "two/letters" / ICONS_FILENAME).parent
        with pytest.raises(FileExistsError):
            install.build_assets(
                [first, second],
                send_mode=install.SendMode.CTRL_V,
                duplicates="skip",
                build_dir=directory / "build",
                assets_dir=assets,
            )


@pytest.mark.parametrize(
    ("answers", "selected"),
    [("0\n1\n", {"tabulator"}), ("\n\n", set()), ("1\n1\n", {"newline", "tabulator"})],
)
def test_install_selects_special_characters_and_retains_independent_build(
    answers: str, selected: set, monkeypatch: pytest.MonkeyPatch
) -> None:
    with temporary_project() as directory:
        build = build_project()
        target = directory / "installed"
        before = snapshot(build)
        (build / install.LOG_FILENAME).write_text("build log")
        assert run_install(target, answers, monkeypatch) == 0
        assert {p.stem for p in (target / SPECIAL_CHARS.name).glob("*.txt")} == selected
        expected = {
            path: data
            for path, data in before.items()
            if path.parts[0] != SPECIAL_CHARS.name or path.stem in selected
        }
        assert snapshot(target) == expected
        assert not (target / install.LOG_FILENAME).exists()
        (target / "letters/U+0041.txt").write_bytes(b"edited")
        assert snapshot(build) == before


def test_reinstall_replaces_entire_target_but_preserves_siblings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with temporary_project() as directory:
        build = build_project()
        target = directory / "installed"
        target.mkdir()
        (target / "obsolete.txt").write_text("obsolete")
        sibling = directory / "personal.txt"
        sibling.write_text("keep")
        assert run_install(target, "invalid\n9\n1\n1\n1\n", monkeypatch) == 0
        assert snapshot(target) == snapshot(build)
        assert sibling.read_text() == "keep"
        assert not list(directory.glob(".installed-*"))


@pytest.mark.parametrize("answers", ["\n", "1\n0\n"])
def test_declining_or_interrupting_prompts_preserves_target_and_build(
    answers: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    with temporary_project() as directory:
        build = build_project()
        target = directory / "installed"
        target.mkdir()
        (target / "keep.txt").write_text("keep")
        before = snapshot(build)
        if answers == "\n":
            assert run_install(target, answers, monkeypatch) == 0
        else:
            with pytest.raises(EOFError):
                run_install(target, answers, monkeypatch)
        assert snapshot(target) == {Path("keep.txt"): b"keep"}
        assert snapshot(build) == before


@pytest.mark.parametrize("dangling", [False, True])
def test_replacing_target_symlink_preserves_external_files(
    *, dangling: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    with temporary_project() as directory:
        build = build_project()
        external = directory / "external"
        external.mkdir()
        (external / "keep.txt").write_text("keep")
        target = directory / "installed"
        target.symlink_to(
            directory / "missing" if dangling else external, target_is_directory=True
        )
        assert run_install(target, "1\n1\n1\n", monkeypatch) == 0
        assert not target.is_symlink()
        assert snapshot(target) == snapshot(build)
        assert (external / "keep.txt").read_text() == "keep"


def test_build_cleanup_unlinks_children_and_rejects_symlink_root() -> None:
    with TemporaryDirectory() as tmpdir:
        directory = Path(tmpdir)
        external = directory / "external"
        external.mkdir()
        (external / "keep.txt").write_text("keep")
        build = directory / "build"
        build.mkdir()
        (build / "stale").symlink_to(external, target_is_directory=True)
        (build / install.LOG_FILENAME).write_text("log")
        install.clear_build_assets(build)
        assert {p.name for p in build.iterdir()} == {install.LOG_FILENAME}
        assert (external / "keep.txt").read_text() == "keep"
        alias = directory / "build-link"
        alias.symlink_to(external, target_is_directory=True)
        with pytest.raises(OSError, match="symlink"):
            install.clear_build_assets(alias)
        assert (external / "keep.txt").read_text() == "keep"


@pytest.mark.parametrize(
    "target", ["build", "build/installed", ".", "autokey/data", "autokey"]
)
def test_unsafe_targets_are_rejected(target: str) -> None:
    with TemporaryDirectory() as tmpdir:
        directory = Path(tmpdir)
        with pytest.raises(
            ValueError, match=r"must be outside|must not be the AutoKey data"
        ):
            install.validate_install_target(
                directory / target,
                build_dir=directory / "build",
                autokey_dir=directory / "autokey/data",
            )


def test_target_checks_resolve_symlink_aliases() -> None:
    with TemporaryDirectory() as tmpdir:
        directory = Path(tmpdir)
        build = directory / "build"
        build.mkdir()
        alias = directory / "alias"
        alias.symlink_to(build, target_is_directory=True)
        with pytest.raises(ValueError, match="outside"):
            install.validate_install_target(
                alias / "installed",
                build_dir=build,
                autokey_dir=directory / "autokey/data",
            )


@pytest.mark.parametrize(
    ("flag", "verbose"), [("--build-only", False), ("--dry-run", True)]
)
def test_build_only_cli_needs_no_autokey_or_input(
    flag: str, *, verbose: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    with (
        temporary_project() as directory,
        redirect_stderr(StringIO()) as stderr,
    ):
        source = write_icons(directory / "collections/letters" / ICONS_FILENAME).parent
        monkeypatch.setattr(
            "builtins.input", lambda _prompt: pytest.fail("Unexpected input prompt")
        )
        result = install.main(
            [flag, *(["--verbose"] if verbose else []), str(source.parent)]
        )
        assert result == 0
        build = install.BUILD_DIR
        assert (build / "letters/U+0041.txt").read_bytes() == b"A"
        metadata = json.loads((build / "letters/U+0041.json").read_text())
        assert metadata["sendMode"] == "<ctrl>+v"
        assert not install.AUTOKEY_DIR.exists()
        log = (build / install.LOG_FILENAME).read_text()
        assert "Registered" in log
        assert "Build complete" in log
        assert "\033[" not in log + stderr.getvalue()
        assert ("DEBUG:" in stderr.getvalue()) == verbose


def test_missing_default_autokey_directory_fails_before_build() -> None:
    with (
        temporary_project(),
        redirect_stderr(StringIO()) as stderr,
    ):
        with pytest.raises(SystemExit) as error:
            install.main([])
        assert error.value.code == 2
        assert "--autokey-directory" in stderr.getvalue()
        assert not install.BUILD_DIR.exists()


def test_default_sources_build_flat_icons_collection() -> None:
    with temporary_project() as directory:
        icons = install.DATA_DIR / ICONS_DIR
        julia = install.DATA_DIR / JULIA_ICONS
        custom = install.DATA_DIR / CUSTOM_ICONS
        write_icons(julia / ICONS_FILENAME)
        write_icons(julia / "extra.tsv", "U+0043\tC\t\\C\tLetter C\n")
        write_icons(
            custom / "a-first.tsv",
            "U+0041\tA\t\\customA\tCustom A\nU+0042\tB\t\\B\tLetter B\n",
        )
        write_icons(custom / "z-last.tsv", "U+0042\tB\t\\otherB\tOther B\n")
        write_icons(icons / "additional/extra.tsv", "U+0044\tD\t\\D\tLetter D\n")
        (icons / "notes.md").write_text("Collection documentation")
        with chdir(directory):
            assert install.main(["--build-only"]) == 0
        build = install.BUILD_DIR
        expected_collections = {
            JULIA_ICONS.name,
            CUSTOM_ICONS.name,
            "additional",
            LATEX_SNIPPETS.name,
            SPECIAL_CHARS.name,
            CUSTOM_SCRIPTS.name,
        }
        actual_collections = {path.name for path in build.iterdir() if path.is_dir()}
        assert actual_collections == expected_collections
        assert (build / JULIA_ICONS.name / "U+0041.txt").read_bytes() == b"A"
        assert (build / JULIA_ICONS.name / "U+0043.txt").read_bytes() == b"C"
        assert (build / CUSTOM_ICONS.name / "U+0041.txt").read_bytes() == b"A"
        assert (build / CUSTOM_ICONS.name / "U+0042.txt").read_bytes() == b"B"
        metadata = json.loads((build / CUSTOM_ICONS.name / "U+0042.json").read_text())
        assert metadata["abbreviation"]["abbreviations"] == ["\\B "]
        assert (build / "additional/U+0044.txt").read_bytes() == b"D"
        assert not (build / EXTENSION_NAME).exists()


def test_late_build_error_preserves_installation_and_logs_failure() -> None:
    with (
        temporary_project() as directory,
        redirect_stdout(StringIO()) as stdout,
    ):
        assets = install.ASSETS_DIR
        source = write_icons(directory / "collections/letters" / ICONS_FILENAME).parent
        target = directory / "installed"
        target.mkdir()
        (target / "keep.txt").write_text("keep")
        (assets / SNIPPET_FILE).write_text("not valid TOML =")
        with pytest.raises(tomllib.TOMLDecodeError):
            install.main(
                [
                    "--autokey-directory",
                    str(target),
                    "--sendmode",
                    "0",
                    str(source.parent),
                ]
            )
        assert "Replace the entire" not in stdout.getvalue()
        build = install.BUILD_DIR
        assert snapshot(target) == {Path("keep.txt"): b"keep"}
        assert (build / "letters/U+0041.txt").read_bytes() == b"A"
        assert "Traceback" in (build / install.LOG_FILENAME).read_text()


def frontend_outputs(
    monkeypatch: pytest.MonkeyPatch, outputs: dict[str, str | OSError]
) -> None:
    monkeypatch.setattr(
        install.shutil,
        "which",
        lambda name, **_kwargs: name if name in outputs else None,
    )

    def run(command, **_kwargs):
        result = outputs[command[0]]
        if isinstance(result, OSError):
            raise result
        return SimpleNamespace(stdout=result)

    monkeypatch.setattr(install.subprocess, "run", run)


@pytest.mark.parametrize("version", ["0.96.0", "0.100.0", "1.0.0", "0.95.10"])
def test_system_version_check_runs_frontend(
    monkeypatch: pytest.MonkeyPatch, version: str
) -> None:
    frontend_outputs(monkeypatch, {"autokey-gtk": f"autokey-gtk Version {version}"})
    if version == "0.95.10":
        with pytest.raises(SystemExit, match=r"found 0\.95\.10"):
            install.check_autokey_version()
    else:
        install.check_autokey_version()


def test_version_check_uses_qt_if_gtk_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    frontend_outputs(
        monkeypatch,
        {"autokey-gtk": OSError("unavailable"), "autokey-qt": "AutoKey 0.95.10"},
    )
    with pytest.raises(SystemExit, match=r"found 0\.95\.10"):
        install.check_autokey_version()


@pytest.mark.parametrize("output", [None, "unknown version", OSError("unavailable")])
def test_missing_or_unreadable_version_warns_and_continues(
    monkeypatch: pytest.MonkeyPatch,
    caplog,
    output: str | OSError | None,
) -> None:
    frontend_outputs(monkeypatch, {} if output is None else {"autokey-gtk": output})
    install.check_autokey_version()
    assert "Could not determine" in caplog.text

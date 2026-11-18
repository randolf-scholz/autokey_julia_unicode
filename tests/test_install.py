"""Exercise generated files and installation transactions on temporary directories."""

import json
import shlex
import shutil
import tomllib
from collections.abc import Iterator
from contextlib import chdir, contextmanager, nullcontext, redirect_stderr
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
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


def run_install(target: Path, answers: str) -> int:
    """Run the CLI in process with a finite stream of prompt answers."""
    with patch("sys.stdin", StringIO(answers)):
        return install.main(["--autokey-directory", str(target), "--sendmode", "1"])


def test_phrase_overrides_preserve_payload() -> None:
    with temporary_project() as directory:
        # Replace the sample snippet with overrides for nested template fields.
        source = install.ASSETS_DIR / LATEX_SNIPPETS.name
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
            source,
            send_mode=install.SendMode.SHIFT_INSERT,
            build_dir=directory,
        )

        # Keep the payload bytes separate from the merged AutoKey metadata.
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
        source = install.ASSETS_DIR / "phrases"
        source.mkdir()
        config = source / "bad.toml"
        config.write_text(contents)
        with pytest.raises(TypeError) as error:
            install.build_phrases(
                source,
                send_mode=install.SendMode.CTRL_V,
                build_dir=directory,
            )
        assert str(config) in str(error.value)
        assert field in str(error.value)


def test_script_payload_and_merged_metadata() -> None:
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
        (install.ASSETS_DIR / SCRIPT_METADATA).write_text(
            "abbreviation.abbreviations = ['!script']"
        )
        with pytest.raises(TypeError, match="description"):
            install.build_custom_scripts(
                install.ASSETS_DIR / CUSTOM_SCRIPTS.name, build_dir=directory
            )


class TestIcons:
    """Check icon parsing, replacement payloads, and collection conflicts."""

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
    def test_builds_supported_replacements(self, rows: str, expected: dict) -> None:
        with temporary_project() as directory:
            # Build a collection containing the parametrized Unicode representation.
            source = write_icons(directory / "icons" / ICONS_FILENAME, rows).parent

            install.build_assets(
                [source],
                send_mode=install.SendMode.CTRL_V,
                duplicates="skip",
                build_dir=directory / "build",
                assets_dir=install.ASSETS_DIR,
            )

            # Compare payload files; unsupported rows must not create replacements.
            actual = {
                p.name: p.read_bytes()
                for p in (directory / "build" / "icons").glob("*.txt")
            }
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
    def test_rejects_invalid_codes(self, row: str, diagnostic: str) -> None:
        with TemporaryDirectory() as tmpdir:
            path = write_icons(Path(tmpdir) / ICONS_FILENAME, row)
            with pytest.raises(ValueError, match=diagnostic):
                install.process_icons(path)

    def test_reordered_columns_and_literal_quotes(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / ICONS_FILENAME
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
    def test_malformed_file_reports_path(self, text: str, diagnostic: str) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / ICONS_FILENAME
            path.write_text(text)
            with pytest.raises(ValueError, match=diagnostic) as error:
                list(install.load_icons(path))
            assert str(path) in str(error.value)

    @pytest.mark.parametrize("policy", ["skip", "error"])
    def test_duplicate_policy(self, policy: Literal["skip", "error"]) -> None:
        with temporary_project() as directory:
            # Both files define A; sorted filenames determine which alias comes first.
            source = write_icons(
                directory / "letters/a-first.tsv",
                "U+0041\tA\t\\first\tLetter A\n",
            ).parent
            write_icons(source / "z-last.tsv")
            with pytest.raises(FileExistsError) if policy == "error" else nullcontext():
                install.build_assets(
                    [source],
                    send_mode=install.SendMode.CTRL_V,
                    duplicates=policy,
                    build_dir=directory / "build",
                    assets_dir=install.ASSETS_DIR,
                )

            if policy == "skip":
                # Skipping duplicates preserves the first definition's metadata.
                metadata = json.loads(
                    (directory / "build/letters/U+0041.json").read_text()
                )
                assert metadata["abbreviation"]["abbreviations"] == ["\\first "]

    def test_rejects_collection_name_collisions(self) -> None:
        with temporary_project() as directory:
            first = write_icons(directory / "one/letters" / ICONS_FILENAME).parent
            second = write_icons(directory / "two/letters" / ICONS_FILENAME).parent
            with pytest.raises(FileExistsError):
                install.build_assets(
                    [first, second],
                    send_mode=install.SendMode.CTRL_V,
                    duplicates="skip",
                    build_dir=directory / "build",
                    assets_dir=install.ASSETS_DIR,
                )


class TestInstallation:
    """Check replacement, prompt selection, and preservation of existing files."""

    @pytest.mark.parametrize(
        ("answers", "selected"),
        [
            ("0\n1\n", {"tabulator"}),
            ("\n\n", set()),
            ("1\n1\n", {"newline", "tabulator"}),
        ],
    )
    def test_selection_preserves_build(self, answers: str, selected: set) -> None:
        with temporary_project() as directory:
            # Record the complete build before choosing optional special characters.
            build = build_project()
            target = directory / "installed"
            before = snapshot(build)
            (build / install.LOG_FILENAME).write_text("build log")

            assert run_install(target, answers) == 0

            # Install only the selected characters, and exclude the build log.
            actual = {p.stem for p in (target / SPECIAL_CHARS.name).glob("*.txt")}
            assert actual == selected
            expected = {
                path: data
                for path, data in before.items()
                if path.parts[0] != SPECIAL_CHARS.name or path.stem in selected
            }
            assert snapshot(target) == expected
            assert not (target / install.LOG_FILENAME).exists()

            # Editing the installed copy must not alter the retained build.
            (target / "letters/U+0041.txt").write_bytes(b"edited")
            assert snapshot(build) == before

    def test_replacement_preserves_siblings(self) -> None:
        with temporary_project() as directory:
            # Place obsolete content inside the target and personal content beside it.
            build = build_project()
            target = directory / "installed"
            target.mkdir()
            (target / "obsolete.txt").write_text("obsolete")
            sibling = directory / "personal.txt"
            sibling.write_text("keep")

            # Retry invalid choices, then approve replacement and both characters.
            assert run_install(target, "invalid\n9\n1\n1\n1\n") == 0

            assert snapshot(target) == snapshot(build)
            assert sibling.read_text() == "keep"
            assert not list(directory.glob(".installed-*"))

    @pytest.mark.parametrize("answers", ["\n", "1\n0\n"])
    def test_cancelled_prompts_preserve_files(self, answers: str) -> None:
        with temporary_project() as directory:
            # Keep snapshots of the build and an existing installation to protect.
            build = build_project()
            target = directory / "installed"
            target.mkdir()
            (target / "keep.txt").write_text("keep")
            before = snapshot(build)

            # Either decline replacement or exhaust input during character selection.
            with nullcontext() if answers == "\n" else pytest.raises(EOFError):
                assert run_install(target, answers) == 0

            assert snapshot(target) == {Path("keep.txt"): b"keep"}
            assert snapshot(build) == before

    @pytest.mark.parametrize("dangling", [False, True])
    def test_symlink_preserves_external_files(self, *, dangling: bool) -> None:
        with temporary_project() as directory:
            # Point the installation at either an external directory or a missing one.
            build = build_project()
            external = directory / "external"
            external.mkdir()
            (external / "keep.txt").write_text("keep")
            target = directory / "installed"
            target.symlink_to(
                directory / "missing" if dangling else external,
                target_is_directory=True,
            )
            assert run_install(target, "1\n1\n1\n") == 0

            # Replace the link itself while preserving files outside the target.
            assert not target.is_symlink()
            assert snapshot(target) == snapshot(build)
            assert (external / "keep.txt").read_text() == "keep"


def test_build_cleanup_unlinks_children_and_rejects_symlink_root() -> None:
    with TemporaryDirectory() as tmpdir:
        # A stale build child points at external content that cleanup must preserve.
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

        # A symlink used as the build root must be rejected before cleanup starts.
        alias = directory / "build-link"
        alias.symlink_to(external, target_is_directory=True)
        with pytest.raises(OSError, match="symlink"):
            install.clear_build_assets(alias)
        assert (external / "keep.txt").read_text() == "keep"


class TestTargetValidation:
    """Check unsafe installation paths and aliases."""

    @pytest.mark.parametrize(
        "target", ["build", "build/installed", ".", "autokey/data", "autokey"]
    )
    def test_rejects_unsafe_paths(self, target: str) -> None:
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

    def test_resolves_symlink_aliases(self) -> None:
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
def test_build_only_needs_no_autokey_or_input(flag: str, *, verbose: bool) -> None:
    with (
        temporary_project() as directory,
        redirect_stderr(StringIO()) as stderr,
        patch("sys.stdin", StringIO("")),
    ):
        source = write_icons(directory / "collections/letters" / ICONS_FILENAME).parent

        # Empty stdin makes any unexpected prompt fail with EOFError.
        result = install.main(
            [flag, *(["--verbose"] if verbose else []), str(source.parent)],
        )
        assert result == 0

        # Generate usable assets without initializing the AutoKey data directory.
        build = install.BUILD_DIR
        assert (build / "letters/U+0041.txt").read_bytes() == b"A"
        metadata = json.loads((build / "letters/U+0041.json").read_text())
        assert metadata["sendMode"] == "<ctrl>+v"
        assert not install.AUTOKEY_DIR.exists()

        # The log retains debug details; console verbosity follows the CLI flag.
        log = (build / install.LOG_FILENAME).read_text()
        assert "Registered" in log
        assert "Build complete" in log
        assert "\033[" not in log + stderr.getvalue()
        assert ("DEBUG:" in stderr.getvalue()) == verbose


def test_missing_autokey_directory_fails_before_build() -> None:
    with (
        temporary_project(),
        redirect_stderr(StringIO()) as stderr,
    ):
        with pytest.raises(SystemExit) as error:
            install.main([])
        assert error.value.code == 2
        assert "--autokey-directory" in stderr.getvalue()
        assert not install.BUILD_DIR.exists()


def test_default_sources_build_flat_collections() -> None:
    with temporary_project() as directory:
        # Populate multiple collections, including duplicate definitions of B.
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

        # Default source paths must work from outside the project directory.
        with chdir(directory):
            assert install.main(["--build-only"]) == 0

        # Each collection gets its own directory directly under the build root.
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

        # Combine files within collections and retain the first duplicate's alias.
        assert (build / JULIA_ICONS.name / "U+0041.txt").read_bytes() == b"A"
        assert (build / JULIA_ICONS.name / "U+0043.txt").read_bytes() == b"C"
        assert (build / CUSTOM_ICONS.name / "U+0041.txt").read_bytes() == b"A"
        assert (build / CUSTOM_ICONS.name / "U+0042.txt").read_bytes() == b"B"
        metadata = json.loads((build / CUSTOM_ICONS.name / "U+0042.json").read_text())
        assert metadata["abbreviation"]["abbreviations"] == ["\\B "]
        assert (build / "additional/U+0044.txt").read_bytes() == b"D"
        assert not (build / EXTENSION_NAME).exists()


def test_build_error_preserves_target(capsys: pytest.CaptureFixture[str]) -> None:
    with temporary_project() as directory:
        # Break a snippet processed after icons, with an existing target in place.
        source = write_icons(directory / "collections/letters" / ICONS_FILENAME).parent
        target = directory / "installed"
        target.mkdir()
        (target / "keep.txt").write_text("keep")
        (install.ASSETS_DIR / SNIPPET_FILE).write_text("not valid TOML =")

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

        # Failure precedes replacement prompts and leaves the installation intact.
        assert "Replace the entire" not in capsys.readouterr().out
        build = install.BUILD_DIR
        assert snapshot(target) == {Path("keep.txt"): b"keep"}

        # Retain the partial build and traceback for diagnosing the failure.
        assert (build / "letters/U+0041.txt").read_bytes() == b"A"
        assert "Traceback" in (build / install.LOG_FILENAME).read_text()


def write_frontend(directory: Path, name: str, output: str | OSError) -> None:
    """Create a real executable for version detection, or one that cannot run."""
    executable = directory / name
    if isinstance(output, OSError):
        executable.write_text("#!/nonexistent/autokey-interpreter\n")
    else:
        executable.write_text(f"#!/bin/sh\nprintf '%s\\n' {shlex.quote(output)}\n")
    executable.chmod(0o755)


class TestVersionDetection:
    """Check frontend execution, fallback, and unavailable version information."""

    @pytest.mark.parametrize("version", ["0.96.0", "0.100.0", "1.0.0", "0.95.10"])
    def test_runs_frontend(self, version: str) -> None:
        with TemporaryDirectory() as tmpdir:
            write_frontend(
                Path(tmpdir), "autokey-gtk", f"autokey-gtk Version {version}"
            )
            if version == "0.95.10":
                with pytest.raises(SystemExit, match=r"found 0\.95\.10"):
                    install.check_autokey_version(tmpdir)
            else:
                install.check_autokey_version(tmpdir)

    def test_falls_back_to_qt(self) -> None:
        with TemporaryDirectory() as tmpdir:
            directory = Path(tmpdir)
            write_frontend(directory, "autokey-gtk", OSError("unavailable"))
            write_frontend(directory, "autokey-qt", "AutoKey 0.95.10")
            with pytest.raises(SystemExit, match=r"found 0\.95\.10"):
                install.check_autokey_version(tmpdir)

    @pytest.mark.parametrize(
        "output", [None, "unknown version", OSError("unavailable")]
    )
    def test_unavailable_version_warns(self, output: str | OSError | None) -> None:
        with (
            TemporaryDirectory() as tmpdir,
            redirect_stderr(StringIO()) as stderr,
            install.installation_logging(Path(tmpdir) / "build", verbose=False),
        ):
            if output is not None:
                write_frontend(Path(tmpdir), "autokey-gtk", output)
            install.check_autokey_version(tmpdir)
        assert "Could not determine" in stderr.getvalue()

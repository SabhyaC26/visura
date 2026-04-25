from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from visura.cli import app


def test_validate_example() -> None:
    result = CliRunner().invoke(app, ["validate", "examples/my-headshot.visura.toml"])

    assert result.exit_code == 0
    assert '"kind": "headshot"' in result.stdout


def test_version() -> None:
    result = CliRunner().invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip()


def test_compile_example() -> None:
    result = CliRunner().invoke(app, ["compile", "examples/workshop-poster.visura.toml"])

    assert result.exit_code == 0
    assert '"kind": "poster"' in result.stdout
    assert '"prompt":' in result.stdout
    assert '"path": "assets/examples/workshop-poster.png"' in result.stdout


def test_compile_unknown_kind(tmp_path: Path) -> None:
    spec_path = tmp_path / "unknown.visura.toml"
    spec_path.write_text(
        """
kind = "unknown"
provider = "mock"
model = "placeholder"

[output]
path = "assets/unknown.png"
alt = "Unknown image."

[content]
subject = "Something"
""",
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["compile", str(spec_path)])

    assert result.exit_code == 1
    assert "Unknown kind: unknown" in result.stderr


def test_compile_missing_kind_content(tmp_path: Path) -> None:
    spec_path = tmp_path / "poster.visura.toml"
    spec_path.write_text(
        """
kind = "poster"
provider = "mock"
model = "placeholder"

[output]
path = "assets/poster.png"
alt = "Poster."

[content]
event = "No headline"
""",
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["compile", str(spec_path)])

    assert result.exit_code == 1
    assert "poster content is missing required field(s): headline" in result.stderr


def test_render_mock_writes_output(tmp_path: Path) -> None:
    with CliRunner().isolated_filesystem(temp_dir=tmp_path):
        spec_path = Path("poster.visura.toml")
        spec_path.write_text(
            """
kind = "poster"
provider = "mock"
model = "placeholder"
size = "512x512"
output_format = "png"

[output]
path = "assets/poster.png"
alt = "Poster."

[content]
headline = "Make Images That Listen"
""",
            encoding="utf-8",
        )

        result = CliRunner().invoke(app, ["render", str(spec_path)])

        assert result.exit_code == 0
        assert Path("assets/poster.png").exists()
        assert '"output_path": "assets/poster.png"' in result.stdout

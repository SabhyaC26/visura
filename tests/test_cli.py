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


def test_compile_preserves_content_order_and_article(tmp_path: Path) -> None:
    spec_path = tmp_path / "anime.visura.toml"
    spec_path.write_text(
        """
kind = "anime_character"
provider = "mock"
model = "placeholder"

[output]
path = "assets/anime.png"
alt = "Anime character."

[content]
character = "inventor"
pose = "holding a tablet"
setting = "workshop"
""",
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["compile", str(spec_path)])

    assert result.exit_code == 0
    assert "Create an anime character image." in result.stdout
    assert result.stdout.index("Character: inventor.") < result.stdout.index("Pose: holding")
    assert result.stdout.index("Pose: holding") < result.stdout.index("Setting: workshop.")


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


def test_render_paid_provider_requires_yes(tmp_path: Path) -> None:
    spec_path = tmp_path / "product.visura.toml"
    spec_path.write_text(
        """
kind = "product_mockup"
provider = "bfl"
model = "flux-2-klein-4b"
size = "1024x1024"
output_format = "png"

[output]
path = "assets/product.png"
alt = "Product mockup."

[content]
product = "desk lamp"
""",
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["render", str(spec_path)])

    assert result.exit_code == 1
    assert "requires --yes" in result.stderr


def test_render_bfl_requires_api_key_with_yes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("BFL_API_KEY", raising=False)
    spec_path = tmp_path / "product.visura.toml"
    spec_path.write_text(
        """
kind = "product_mockup"
provider = "bfl"
model = "flux-2-klein-4b"
size = "1024x1024"
output_format = "png"

[output]
path = "assets/product.png"
alt = "Product mockup."

[content]
product = "desk lamp"
""",
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["render", str(spec_path), "--yes"])

    assert result.exit_code == 1
    assert "BFL_API_KEY is required" in result.stderr

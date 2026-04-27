from __future__ import annotations

import json
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
        assert Path("assets/poster.visura.json").exists()


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


def test_render_mock_writes_sidecar_and_cache_metadata(tmp_path: Path) -> None:
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
        payload = json.loads(result.stdout)
        sidecar = json.loads(Path("assets/poster.visura.json").read_text(encoding="utf-8"))

        assert payload["cache"] == "miss"
        assert payload["sidecar_path"] == "assets/poster.visura.json"
        assert payload["render_hash"].startswith("sha256:")
        assert payload["output_digest"].startswith("sha256:")
        assert sidecar["schema_version"] == "0.1"
        assert sidecar["cache"] == "miss"
        assert sidecar["spec"]["output"]["path"] == "assets/poster.png"
        assert sidecar["payload"]["prompt"]
        assert Path(".visura/cache").exists()


def test_render_mock_restores_deleted_output_from_cache(tmp_path: Path) -> None:
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

        first = CliRunner().invoke(app, ["render", str(spec_path)])
        Path("assets/poster.png").unlink()
        second = CliRunner().invoke(app, ["render", str(spec_path)])

        first_payload = json.loads(first.stdout)
        second_payload = json.loads(second.stdout)
        sidecar = json.loads(Path("assets/poster.visura.json").read_text(encoding="utf-8"))

        assert first.exit_code == 0
        assert second.exit_code == 0
        assert Path("assets/poster.png").exists()
        assert second_payload["cache"] == "hit"
        assert second_payload["render_hash"] == first_payload["render_hash"]
        assert second_payload["output_digest"] == first_payload["output_digest"]
        assert sidecar["cache"] == "hit"


def test_render_mock_force_refreshes_cache(tmp_path: Path) -> None:
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

        first = CliRunner().invoke(app, ["render", str(spec_path)])
        forced = CliRunner().invoke(app, ["render", str(spec_path), "--force"])

        first_payload = json.loads(first.stdout)
        forced_payload = json.loads(forced.stdout)

        assert first.exit_code == 0
        assert forced.exit_code == 0
        assert forced_payload["cache"] == "refresh"
        assert forced_payload["render_hash"] == first_payload["render_hash"]
        assert forced_payload["output_digest"] == first_payload["output_digest"]


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


def test_status_reports_clean_rendered_asset(tmp_path: Path) -> None:
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

        render = CliRunner().invoke(app, ["render", str(spec_path)])
        result = CliRunner().invoke(app, ["status", str(spec_path)])

        assert render.exit_code == 0
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload[0]["ok"] is True
        assert payload[0]["state"] == "clean"
        assert payload[0]["output_exists"] is True
        assert payload[0]["sidecar_exists"] is True
        assert payload[0]["cache_exists"] is True
        assert payload[0]["current_render_hash"] == payload[0]["sidecar_render_hash"]


def test_status_reports_stale_after_spec_change(tmp_path: Path) -> None:
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
        render = CliRunner().invoke(app, ["render", str(spec_path)])

        spec_path.write_text(
            spec_path.read_text(encoding="utf-8").replace(
                'headline = "Make Images That Listen"',
                'headline = "Make Images That Remember"',
            ),
            encoding="utf-8",
        )
        result = CliRunner().invoke(app, ["status", str(spec_path)])

        assert render.exit_code == 0
        assert result.exit_code == 1
        payload = json.loads(result.stdout)
        assert payload[0]["ok"] is False
        assert payload[0]["state"] == "stale"
        assert payload[0]["current_render_hash"] != payload[0]["sidecar_render_hash"]


def test_status_reports_missing_sidecar(tmp_path: Path) -> None:
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
        render = CliRunner().invoke(app, ["render", str(spec_path)])
        Path("assets/poster.visura.json").unlink()

        result = CliRunner().invoke(app, ["status", str(spec_path)])

        assert render.exit_code == 0
        assert result.exit_code == 1
        payload = json.loads(result.stdout)
        assert payload[0]["ok"] is False
        assert payload[0]["state"] == "missing_sidecar"
        assert payload[0]["output_exists"] is True
        assert payload[0]["sidecar_exists"] is False


def test_status_reports_invalid_spec(tmp_path: Path) -> None:
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

    result = CliRunner().invoke(app, ["status", str(spec_path)])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload[0]["ok"] is False
    assert payload[0]["state"] == "invalid"
    assert "poster content is missing required field(s): headline" in payload[0]["error"]

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_visura(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "from visura.cli import app; app()",
            *args,
        ],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def write_poster_spec(project: Path) -> Path:
    spec_path = project / "assets" / "workshop-poster.visura.toml"
    spec_path.parent.mkdir(parents=True)
    spec_path.write_text(
        """
kind = "poster"
provider = "mock"
model = "placeholder"
size = "512x512"
quality = "draft"
output_format = "png"

[output]
path = "assets/workshop-poster.png"
alt = "Risograph-style workshop poster."

[style]
medium = "risograph event poster"
mood = "hands-on, lively"
palette = ["tomato red", "deep teal", "warm paper"]

[content]
event = "Prompt Craft Night"
headline = "Make Images That Listen"
details = "Friday, 7 PM"
visual = "hands arranging prompt cards around a monitor"
""",
        encoding="utf-8",
    )
    return spec_path


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_e2e_validate_compile_render_and_cache_restore(tmp_path: Path) -> None:
    spec_path = write_poster_spec(tmp_path)

    validate = run_visura(tmp_path, "validate", str(spec_path))
    assert validate.returncode == 0
    validated = json.loads(validate.stdout)
    assert validated["kind"] == "poster"
    assert validated["output"]["path"] == "assets/workshop-poster.png"

    compile_result = run_visura(tmp_path, "compile", str(spec_path))
    assert compile_result.returncode == 0
    compiled = json.loads(compile_result.stdout)
    assert compiled["kind"] == "poster"
    assert "Make Images That Listen" in compiled["prompt"]
    assert compiled["output"]["path"] == "assets/workshop-poster.png"

    first_render = run_visura(tmp_path, "render", str(spec_path))
    assert first_render.returncode == 0
    first_payload = json.loads(first_render.stdout)
    assert first_payload["cache"] == "miss"
    assert first_payload["render_hash"].startswith("sha256:")
    assert first_payload["output_digest"].startswith("sha256:")

    output_path = tmp_path / "assets" / "workshop-poster.png"
    sidecar_path = tmp_path / "assets" / "workshop-poster.visura.json"
    cache_dir = tmp_path / ".visura" / "cache"
    assert output_path.exists()
    assert sidecar_path.exists()
    assert any(cache_dir.iterdir())

    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    assert sidecar["cache"] == "miss"
    assert sidecar["render_hash"] == first_payload["render_hash"]
    assert sidecar["payload"]["prompt"] == compiled["prompt"]

    output_path.unlink()
    second_render = run_visura(tmp_path, "render", str(spec_path))
    assert second_render.returncode == 0
    second_payload = json.loads(second_render.stdout)
    assert second_payload["cache"] == "hit"
    assert second_payload["render_hash"] == first_payload["render_hash"]
    assert second_payload["output_digest"] == first_payload["output_digest"]
    assert output_path.exists()


def test_e2e_force_refresh_updates_sidecar_without_changing_hash(tmp_path: Path) -> None:
    spec_path = write_poster_spec(tmp_path)

    first_render = run_visura(tmp_path, "render", str(spec_path))
    forced_render = run_visura(tmp_path, "render", str(spec_path), "--force")

    assert first_render.returncode == 0
    assert forced_render.returncode == 0
    first_payload = json.loads(first_render.stdout)
    forced_payload = json.loads(forced_render.stdout)
    sidecar = read_json(tmp_path / "assets" / "workshop-poster.visura.json")

    assert first_payload["cache"] == "miss"
    assert forced_payload["cache"] == "refresh"
    assert forced_payload["render_hash"] == first_payload["render_hash"]
    assert forced_payload["output_digest"] == first_payload["output_digest"]
    assert sidecar["cache"] == "refresh"


def test_e2e_spec_change_invalidates_render_cache(tmp_path: Path) -> None:
    spec_path = write_poster_spec(tmp_path)

    first_render = run_visura(tmp_path, "render", str(spec_path))
    assert first_render.returncode == 0
    first_payload = json.loads(first_render.stdout)

    text = spec_path.read_text(encoding="utf-8")
    spec_path.write_text(
        text.replace(
            'headline = "Make Images That Listen"',
            'headline = "Make Images That Remember"',
        ),
        encoding="utf-8",
    )

    second_render = run_visura(tmp_path, "render", str(spec_path))
    assert second_render.returncode == 0
    second_payload = json.loads(second_render.stdout)
    sidecar = read_json(tmp_path / "assets" / "workshop-poster.visura.json")

    assert second_payload["cache"] == "miss"
    assert second_payload["render_hash"] != first_payload["render_hash"]
    assert second_payload["output_digest"] != first_payload["output_digest"]
    assert "Make Images That Remember" in sidecar["payload"]["prompt"]


def test_e2e_invalid_spec_exits_nonzero_without_artifacts(tmp_path: Path) -> None:
    spec_path = tmp_path / "assets" / "broken.visura.toml"
    spec_path.parent.mkdir(parents=True)
    spec_path.write_text(
        """
kind = "poster"
provider = "mock"
model = "placeholder"

[output]
path = "assets/broken.png"
alt = "Broken poster."

[content]
event = "Missing headline"
""",
        encoding="utf-8",
    )

    compile_result = run_visura(tmp_path, "compile", str(spec_path))
    render_result = run_visura(tmp_path, "render", str(spec_path))

    assert compile_result.returncode == 1
    assert render_result.returncode == 1
    assert "poster content is missing required field(s): headline" in compile_result.stderr
    assert "poster content is missing required field(s): headline" in render_result.stderr
    assert not (tmp_path / "assets" / "broken.png").exists()
    assert not (tmp_path / "assets" / "broken.visura.json").exists()
    assert not (tmp_path / ".visura").exists()


def test_e2e_unknown_top_level_field_reports_validation_error(tmp_path: Path) -> None:
    spec_path = tmp_path / "assets" / "unknown-field.visura.toml"
    spec_path.parent.mkdir(parents=True)
    spec_path.write_text(
        """
kind = "poster"
provider = "mock"
model = "placeholder"
surprise = true

[output]
path = "assets/unknown-field.png"
alt = "Poster."

[content]
headline = "Make Images That Listen"
""",
        encoding="utf-8",
    )

    result = run_visura(tmp_path, "validate", str(spec_path))

    assert result.returncode == 1
    assert "surprise: Extra inputs are not permitted" in result.stderr
    assert result.stdout == ""


def test_e2e_paid_provider_requires_explicit_yes(tmp_path: Path) -> None:
    spec_path = tmp_path / "assets" / "paid.visura.toml"
    spec_path.parent.mkdir(parents=True)
    spec_path.write_text(
        """
kind = "product_mockup"
provider = "bfl"
model = "flux-2-klein-4b"
size = "1024x1024"
output_format = "png"

[output]
path = "assets/paid.png"
alt = "Product mockup."

[content]
product = "desk lamp"
""",
        encoding="utf-8",
    )

    result = run_visura(tmp_path, "render", str(spec_path))

    assert result.returncode == 1
    assert "requires --yes" in result.stderr
    assert not (tmp_path / "assets" / "paid.png").exists()


def test_e2e_status_discovers_specs_and_reports_asset_state(tmp_path: Path) -> None:
    spec_path = write_poster_spec(tmp_path)
    missing_spec_path = tmp_path / "assets" / "missing-output.visura.toml"
    missing_spec_path.write_text(
        """
kind = "poster"
provider = "mock"
model = "placeholder"
size = "512x512"
output_format = "png"

[output]
path = "assets/missing-output.png"
alt = "Missing output poster."

[content]
headline = "Make Images That Listen"
""",
        encoding="utf-8",
    )

    render = run_visura(tmp_path, "render", str(spec_path))
    status = run_visura(tmp_path, "status", "assets")

    assert render.returncode == 0
    assert status.returncode == 1
    payload = json.loads(status.stdout)
    by_path = {item["spec_path"]: item for item in payload}

    rendered = by_path[str(spec_path.relative_to(tmp_path))]
    missing = by_path[str(missing_spec_path.relative_to(tmp_path))]

    assert rendered["state"] == "clean"
    assert rendered["ok"] is True
    assert rendered["cache_exists"] is True
    assert missing["state"] == "missing_output"
    assert missing["ok"] is False
    assert missing["sidecar_exists"] is False

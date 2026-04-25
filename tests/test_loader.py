from __future__ import annotations

from pathlib import Path

import pytest

from visura.backends import registered_backends
from visura.kinds import registered_kinds
from visura.loader import SpecLoadError, load_spec


def write_spec(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "spec.visura.toml"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize("example_path", sorted(Path("examples").glob("*.visura.toml")))
def test_loads_example_specs(example_path: Path) -> None:
    spec = load_spec(example_path)

    assert spec.kind
    assert spec.provider
    assert spec.model
    assert spec.content


def test_loads_headshot_example_content() -> None:
    spec = load_spec("examples/my-headshot.visura.toml")

    assert spec.kind == "headshot"
    assert spec.provider == "openai"
    assert spec.model == "gpt-image-1"
    assert spec.content["subject"] == "Sabhya, a software builder"


def test_missing_required_field_reports_location(tmp_path: Path) -> None:
    path = write_spec(
        tmp_path,
        """
kind = "headshot"

[content]
subject = "A person"
""",
    )

    with pytest.raises(SpecLoadError, match="model: Field required"):
        load_spec(path)


def test_wrong_type_reports_location(tmp_path: Path) -> None:
    path = write_spec(
        tmp_path,
        """
kind = "headshot"
model = "example-model"
seed = "not-a-number"

[content]
subject = "A person"
""",
    )

    with pytest.raises(SpecLoadError, match="seed: Input should be a valid integer"):
        load_spec(path)


def test_unknown_top_level_key_reports_location(tmp_path: Path) -> None:
    path = write_spec(
        tmp_path,
        """
kind = "headshot"
model = "example-model"
surprise = true

[content]
subject = "A person"
""",
    )

    with pytest.raises(SpecLoadError, match="surprise: Extra inputs are not permitted"):
        load_spec(path)


def test_malformed_toml_reports_parse_error(tmp_path: Path) -> None:
    path = write_spec(
        tmp_path,
        """
kind = "headshot
""",
    )

    with pytest.raises(SpecLoadError, match="Malformed TOML"):
        load_spec(path)


def test_m1_has_no_registered_kinds_yet() -> None:
    assert registered_kinds() == ()


def test_default_backend_is_registered() -> None:
    assert registered_backends() == ("openai",)

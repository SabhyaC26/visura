from __future__ import annotations

from pathlib import Path

import pytest

from visura.backends import get_backend, registered_backends
from visura.kinds import registered_kinds
from visura.loader import SpecLoadError, load_spec
from visura.spec import Spec


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
    assert spec.output.path
    assert spec.output.alt
    assert spec.content


def test_loads_headshot_example_content() -> None:
    spec = load_spec("examples/my-headshot.visura.toml")

    assert spec.kind == "headshot"
    assert spec.provider == "openai"
    assert spec.model == "gpt-image-1"
    assert spec.output.path == Path("assets/examples/my-headshot.png")
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


def test_missing_output_reports_location(tmp_path: Path) -> None:
    path = write_spec(
        tmp_path,
        """
kind = "headshot"
model = "example-model"

[content]
subject = "A person"
""",
    )

    with pytest.raises(SpecLoadError, match="output: Field required"):
        load_spec(path)


def test_unknown_output_key_reports_location(tmp_path: Path) -> None:
    path = write_spec(
        tmp_path,
        """
kind = "headshot"
model = "example-model"

[output]
path = "assets/person.png"
alt = "Headshot of a person."
surprise = true

[content]
subject = "A person"
""",
    )

    with pytest.raises(SpecLoadError, match="output.surprise: Extra inputs are not permitted"):
        load_spec(path)


def test_blank_output_alt_reports_location(tmp_path: Path) -> None:
    path = write_spec(
        tmp_path,
        """
kind = "headshot"
model = "example-model"

[output]
path = "assets/person.png"
alt = "  "

[content]
subject = "A person"
""",
    )

    with pytest.raises(SpecLoadError, match="output.alt: Value error, alt must not be blank"):
        load_spec(path)


def test_absolute_output_path_reports_location(tmp_path: Path) -> None:
    path = write_spec(
        tmp_path,
        """
kind = "headshot"
model = "example-model"

[output]
path = "/tmp/person.png"
alt = "Headshot of a person."

[content]
subject = "A person"
""",
    )

    with pytest.raises(SpecLoadError, match="output.path: Value error, path must be relative"):
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


def test_builtin_kinds_are_registered() -> None:
    assert registered_kinds() == (
        "blueprint",
        "headshot",
        "infographic",
        "poster",
        "product_mockup",
    )


def test_default_backend_is_registered() -> None:
    assert registered_backends() == ("bfl", "mock", "openai")


def test_bfl_backend_accepts_flux_klein() -> None:
    spec = Spec(
        kind="product_mockup",
        provider="bfl",
        model="flux-2-klein-4b",
        size="1024x1024",
        output_format="png",
        output={"path": "assets/desk-lamp.png", "alt": "Product mockup of a desk lamp."},
        content={"product": "desk lamp"},
    )

    get_backend("bfl").validate_options(spec)


def test_bfl_backend_rejects_webp() -> None:
    spec = Spec(
        kind="product_mockup",
        provider="bfl",
        model="flux-2-klein-4b",
        size="1024x1024",
        output_format="webp",
        output={"path": "assets/desk-lamp.webp", "alt": "Product mockup of a desk lamp."},
        content={"product": "desk lamp"},
    )

    with pytest.raises(ValueError, match="Unsupported output format for bfl: webp"):
        get_backend("bfl").validate_options(spec)


def test_bfl_backend_rejects_non_multiple_of_16_size() -> None:
    spec = Spec(
        kind="product_mockup",
        provider="bfl",
        model="flux-2-klein-4b",
        size="1025x1024",
        output_format="png",
        output={"path": "assets/desk-lamp.png", "alt": "Product mockup of a desk lamp."},
        content={"product": "desk lamp"},
    )

    with pytest.raises(ValueError, match="dimensions must be multiples of 16"):
        get_backend("bfl").validate_options(spec)

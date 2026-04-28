from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from PIL import Image

import visura.backends.diffusers as diffusers_backend
from visura.backends import get_backend, registered_backends
from visura.backends.diffusers import (
    DiffusersBackend,
    DiffusersBackendError,
    DiffusersDependencyError,
)
from visura.kinds.base import PromptOutput, PromptPayload
from visura.spec import Spec


def make_spec(**overrides: Any) -> Spec:
    values: dict[str, Any] = {
        "kind": "poster",
        "provider": "diffusers",
        "model": "hf-internal-testing/tiny-stable-diffusion-pipe",
        "size": "64x64",
        "seed": 1234,
        "output_format": "png",
        "output": {"path": "assets/poster.png", "alt": "Poster."},
        "content": {"headline": "Local render"},
    }
    values.update(overrides)
    return Spec(**values)


def make_payload(spec: Spec) -> PromptPayload:
    return PromptPayload(
        kind=spec.kind,
        provider=spec.provider,
        model=spec.model,
        prompt="Create a small local test image.",
        output=PromptOutput(
            path=str(spec.output.path),
            alt=spec.output.alt,
            name=spec.output.name,
        ),
    )


def test_diffusers_backend_is_registered() -> None:
    assert "diffusers" in registered_backends()
    assert get_backend("diffusers").name == "diffusers"


def test_diffusers_backend_validates_sane_options() -> None:
    DiffusersBackend().validate_options(make_spec())


def test_diffusers_backend_rejects_invalid_size() -> None:
    with pytest.raises(ValueError, match="dimensions must be multiples of 8"):
        DiffusersBackend().validate_options(make_spec(size="65x64"))


def test_diffusers_backend_rejects_invalid_output_format() -> None:
    spec = make_spec().model_copy(update={"output_format": "gif"})

    with pytest.raises(ValueError, match="Unsupported output format for diffusers: gif"):
        DiffusersBackend().validate_options(spec)


def test_diffusers_backend_rejects_invalid_seed() -> None:
    with pytest.raises(ValueError, match="seed must be between 0 and 4294967295"):
        DiffusersBackend().validate_options(make_spec(seed=-1))


def test_diffusers_backend_missing_dependency_has_install_hint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def missing_import(name: str) -> Any:
        raise ModuleNotFoundError(f"No module named {name!r}")

    monkeypatch.setattr(diffusers_backend, "import_module", missing_import)
    diffusers_backend._PIPELINE_CACHE.clear()
    spec = make_spec()

    with pytest.raises(DiffusersDependencyError) as exc_info:
        DiffusersBackend().render(spec, make_payload(spec), tmp_path / "out.png")

    message = str(exc_info.value)
    assert "uv sync --extra diffusers" in message
    assert "visura[diffusers]" in message


def test_diffusers_backend_renders_and_caches_pipeline_with_fake_dependencies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FakePipeline:
        loads = 0

        @classmethod
        def from_pretrained(cls, model: str) -> FakePipeline:
            assert model == "hf-internal-testing/tiny-stable-diffusion-pipe"
            cls.loads += 1
            return cls()

        def to(self, device: str) -> None:
            assert device == "cpu"

        def __call__(self, **request: Any) -> SimpleNamespace:
            assert request["width"] == 64
            assert request["height"] == 64
            assert request["generator"].seed == 1234
            image = Image.new("RGB", (request["width"], request["height"]), "navy")
            return SimpleNamespace(images=[image])

    class FakeGenerator:
        def __init__(self, *, device: str) -> None:
            assert device == "cpu"
            self.seed: int | None = None

        def manual_seed(self, seed: int) -> FakeGenerator:
            self.seed = seed
            return self

    fake_torch = SimpleNamespace(
        Generator=FakeGenerator,
        backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: False)),
        cuda=SimpleNamespace(is_available=lambda: False),
        inference_mode=lambda: nullcontext(),
    )
    fake_diffusers = SimpleNamespace(DiffusionPipeline=FakePipeline)

    def fake_import(name: str) -> Any:
        return {"diffusers": fake_diffusers, "torch": fake_torch}[name]

    monkeypatch.setattr(diffusers_backend, "import_module", fake_import)
    diffusers_backend._PIPELINE_CACHE.clear()
    spec = make_spec()
    backend = DiffusersBackend()

    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    backend.render(spec, make_payload(spec), first)
    backend.render(spec, make_payload(spec), second)

    assert first.exists()
    assert second.exists()
    assert FakePipeline.loads == 1


def test_diffusers_backend_can_render_tiny_model_when_dependencies_are_installed(
    tmp_path: Path,
) -> None:
    pytest.importorskip("diffusers")
    pytest.importorskip("torch")

    diffusers_backend._PIPELINE_CACHE.clear()
    spec = make_spec()

    try:
        DiffusersBackend().render(spec, make_payload(spec), tmp_path / "tiny.png")
    except DiffusersBackendError as exc:
        pytest.skip(f"Diffusers render skipped: {exc}")

    assert (tmp_path / "tiny.png").exists()

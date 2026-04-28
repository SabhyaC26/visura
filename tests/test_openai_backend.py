from __future__ import annotations

import base64
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from visura.backends.openai import OpenAIBackend, OpenAIRenderError
from visura.kinds.base import PromptOutput, PromptPayload
from visura.render import render_with_cache
from visura.spec import Spec


def make_spec(**overrides: Any) -> Spec:
    data: dict[str, Any] = {
        "kind": "poster",
        "provider": "openai",
        "model": "gpt-image-1",
        "size": "1024x1024",
        "quality": "high",
        "output_format": "png",
        "output": {"path": "assets/poster.png", "alt": "Poster."},
        "content": {"headline": "Make Images That Listen"},
    }
    data.update(overrides)
    return Spec(**data)


def make_payload(spec: Spec, prompt: str = "Create a poster.") -> PromptPayload:
    return PromptPayload(
        kind=spec.kind,
        provider=spec.provider,
        model=spec.model,
        prompt=prompt,
        options={
            "size": spec.size,
            "quality": spec.quality,
            "output_format": spec.output_format,
        },
        references=[],
        output=PromptOutput(
            path=str(spec.output.path),
            alt=spec.output.alt,
            name=spec.output.name,
        ),
    )


def test_openai_render_requires_api_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    spec = make_spec()

    with pytest.raises(OpenAIRenderError, match="OPENAI_API_KEY is required"):
        OpenAIBackend().render(spec, make_payload(spec), tmp_path / "poster.png")


def test_openai_render_calls_sdk_and_writes_decoded_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image_bytes = b"fake image bytes"
    encoded = base64.b64encode(image_bytes).decode("ascii")
    calls: dict[str, Any] = {}

    class FakeImages:
        def generate(self, **request: Any) -> SimpleNamespace:
            calls["request"] = request
            return SimpleNamespace(data=[SimpleNamespace(b64_json=encoded)])

    class FakeOpenAI:
        def __init__(self, *, api_key: str) -> None:
            calls["api_key"] = api_key
            self.images = FakeImages()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("visura.backends.openai.OpenAI", FakeOpenAI)

    spec = make_spec(size="1024x1536", output_format="webp", background="opaque")
    payload = make_payload(spec, prompt="A compact launch poster.")
    output_path = tmp_path / "nested" / "poster.webp"

    OpenAIBackend().render(spec, payload, output_path)

    assert output_path.read_bytes() == image_bytes
    assert calls["api_key"] == "test-key"
    assert calls["request"] == {
        "model": "gpt-image-1",
        "prompt": "A compact launch poster.",
        "n": 1,
        "size": "1024x1536",
        "output_format": "webp",
        "quality": "high",
        "background": "opaque",
    }


def test_openai_unsupported_seed_fails_before_sdk_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingOpenAI:
        def __init__(self, *, api_key: str) -> None:
            raise AssertionError("OpenAI SDK should not be constructed")

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("visura.backends.openai.OpenAI", FailingOpenAI)
    spec = make_spec(seed=1234)

    with pytest.raises(ValueError, match="Seed is not supported by openai/gpt-image-1"):
        OpenAIBackend().render(spec, make_payload(spec), tmp_path / "poster.png")


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"model": "dall-e-3"}, "Unsupported model for openai"),
        ({"size": "512x512"}, "Unsupported size for openai"),
        ({"quality": "draft"}, "Unsupported quality for openai"),
        ({"background": "studio wall"}, "Unsupported background for openai"),
        (
            {"background": "transparent", "output_format": "jpeg"},
            "transparent requires png or webp",
        ),
        (
            {"references": [{"path": "references/selfie.jpg", "role": "likeness"}]},
            "References are not supported by openai/gpt-image-1 generation",
        ),
    ],
)
def test_openai_unsupported_options_validate_clearly(
    overrides: dict[str, Any],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        OpenAIBackend().validate_options(make_spec(**overrides))


def test_openai_render_works_with_cache_and_sidecar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image_bytes = b"cached openai image"
    encoded = base64.b64encode(image_bytes).decode("ascii")
    calls: list[dict[str, Any]] = []

    class FakeImages:
        def generate(self, **request: Any) -> dict[str, Any]:
            calls.append(request)
            return {"data": [{"b64_json": encoded}]}

    class FakeOpenAI:
        def __init__(self, *, api_key: str) -> None:
            self.images = FakeImages()

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("visura.backends.openai.OpenAI", FakeOpenAI)

    spec_path = Path("poster.visura.toml")
    output_path = Path("assets/poster.png")
    spec = make_spec()
    payload = make_payload(spec)

    result = render_with_cache(
        spec_path=spec_path,
        spec=spec,
        payload=payload,
        backend=OpenAIBackend(),
        output_path=output_path,
    )

    sidecar_path = Path("assets/poster.visura.json")
    cache_path = next(Path(".visura/cache").iterdir())
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))

    assert output_path.read_bytes() == image_bytes
    assert cache_path.read_bytes() == image_bytes
    assert result.cache == "miss"
    assert sidecar["provider"] == "openai"
    assert sidecar["cache"] == "miss"
    assert len(calls) == 1

from __future__ import annotations

import base64
import binascii
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from openai import OpenAI, OpenAIError

from visura.backends.base import BackendCapabilities
from visura.kinds.base import PromptPayload
from visura.spec import Spec


class OpenAIRenderError(ValueError):
    """Raised when OpenAI rendering fails."""


class OpenAIBackend:
    name = "openai"
    models = ("gpt-image-1",)
    qualities = ("low", "medium", "high", "auto")
    backgrounds = ("transparent", "opaque", "auto")
    capabilities = BackendCapabilities(
        supports_references=False,
        supports_seed=False,
        output_formats=("png", "jpeg", "webp"),
        sizes=("1024x1024", "1536x1024", "1024x1536", "auto"),
    )

    def validate_options(self, spec: Spec) -> None:
        if spec.model not in self.models:
            supported = ", ".join(self.models)
            raise ValueError(
                f"Unsupported model for {self.name}: {spec.model}. Supported: {supported}"
            )
        if spec.output_format not in self.capabilities.output_formats:
            raise ValueError(f"Unsupported output format for {self.name}: {spec.output_format}")
        if self.capabilities.sizes is not None and spec.size not in self.capabilities.sizes:
            supported = ", ".join(self.capabilities.sizes)
            raise ValueError(
                f"Unsupported size for {self.name}: {spec.size}. Supported: {supported}"
            )
        if spec.quality is not None and spec.quality not in self.qualities:
            supported = ", ".join(self.qualities)
            raise ValueError(
                f"Unsupported quality for {self.name}: {spec.quality}. Supported: {supported}"
            )
        if spec.background is not None and spec.background not in self.backgrounds:
            supported = ", ".join(self.backgrounds)
            raise ValueError(
                f"Unsupported background for {self.name}: {spec.background}. Supported: {supported}"
            )
        if spec.background == "transparent" and spec.output_format == "jpeg":
            raise ValueError(
                "Unsupported background for openai: transparent requires png or webp output"
            )
        if spec.seed is not None:
            raise ValueError("Seed is not supported by openai/gpt-image-1")
        if spec.references:
            raise ValueError("References are not supported by openai/gpt-image-1 generation")

    def render(self, spec: Spec, payload: PromptPayload, output_path: Path) -> None:
        self.validate_options(spec)

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise OpenAIRenderError("OPENAI_API_KEY is required for provider: openai")

        request: dict[str, Any] = {
            "model": spec.model,
            "prompt": payload.prompt,
            "n": 1,
            "size": spec.size,
            "output_format": spec.output_format,
        }
        if spec.quality is not None:
            request["quality"] = spec.quality
        if spec.background is not None:
            request["background"] = spec.background

        try:
            response = OpenAI(api_key=api_key).images.generate(**request)
        except OpenAIError as exc:
            raise OpenAIRenderError(f"OpenAI image generation failed: {exc}") from exc

        image_bytes = _decode_first_image(response)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_bytes)


def _decode_first_image(response: object) -> bytes:
    b64_json = _first_image_field(response, "b64_json")
    if not isinstance(b64_json, str) or not b64_json:
        raise OpenAIRenderError("OpenAI response did not include data[0].b64_json")
    try:
        return base64.b64decode(b64_json, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise OpenAIRenderError("OpenAI response data[0].b64_json was not valid base64") from exc


def _first_image_field(response: object, field: str) -> object:
    data = _field(response, "data")
    if not data:
        return None
    first = data[0]
    return _field(first, field)


def _field(value: object, field: str) -> object:
    if isinstance(value, Mapping):
        return value.get(field)
    return getattr(value, field, None)

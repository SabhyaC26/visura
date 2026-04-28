from __future__ import annotations

import re
from importlib import import_module
from pathlib import Path
from typing import Any

from visura.backends.base import BackendCapabilities
from visura.kinds.base import PromptPayload
from visura.spec import Spec

_INSTALL_HINT = (
    "Diffusers backend requires optional dependencies: diffusers, torch, and "
    "transformers. Install them with `uv sync --extra diffusers` from this repo "
    "or `python -m pip install 'visura[diffusers]'`."
)
_PIPELINE_CACHE: dict[tuple[str, str], Any] = {}


class DiffusersBackendError(ValueError):
    """Raised when local Diffusers rendering cannot complete."""


class DiffusersDependencyError(DiffusersBackendError):
    """Raised when optional Diffusers dependencies are not installed."""


class DiffusersBackend:
    name = "diffusers"
    capabilities = BackendCapabilities(
        supports_references=False,
        supports_seed=True,
        output_formats=("png", "jpeg", "webp"),
        sizes=None,
    )

    def validate_options(self, spec: Spec) -> None:
        if spec.output_format not in self.capabilities.output_formats:
            raise ValueError(f"Unsupported output format for {self.name}: {spec.output_format}")
        if spec.references:
            raise ValueError(f"References are not supported by {self.name} text-to-image models")
        if spec.seed is not None and not 0 <= spec.seed <= 2**32 - 1:
            raise ValueError(
                f"Unsupported seed for {self.name}: seed must be between 0 and 4294967295"
            )

        width, height = _parse_size(spec.size)
        if width % 8 != 0 or height % 8 != 0:
            raise ValueError(
                f"Unsupported size for {self.name}: dimensions must be multiples of 8"
            )
        if width < 64 or height < 64:
            raise ValueError(f"Unsupported size for {self.name}: dimensions must be at least 64x64")
        if width * height > 4_000_000:
            raise ValueError(
                f"Unsupported size for {self.name}: output must not exceed 4 megapixels"
            )

    def render(self, spec: Spec, payload: PromptPayload, output_path: Path) -> None:
        self.validate_options(spec)
        width, height = _parse_size(spec.size)
        diffusion_pipeline, torch = _import_dependencies()
        device = _device_for(torch)
        pipeline = _pipeline_for(
            model=spec.model,
            device=device,
            diffusion_pipeline=diffusion_pipeline,
        )

        request: dict[str, Any] = {
            "prompt": payload.prompt,
            "width": width,
            "height": height,
        }
        if payload.negative_prompt:
            request["negative_prompt"] = payload.negative_prompt
        if spec.seed is not None:
            request["generator"] = torch.Generator(device="cpu").manual_seed(spec.seed)

        try:
            with torch.inference_mode():
                result = pipeline(**request)
        except Exception as exc:  # pragma: no cover - depends on model/runtime internals
            raise DiffusersBackendError(f"Diffusers generation failed: {exc}") from exc

        images = getattr(result, "images", None)
        if not images:
            raise DiffusersBackendError("Diffusers generation did not return any images")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        _save_image(images[0], output_path, spec.output_format)


def _parse_size(size: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d+)x(\d+)", size)
    if match is None:
        raise ValueError(f"Unsupported size for diffusers: expected WIDTHxHEIGHT, got {size!r}")
    return int(match.group(1)), int(match.group(2))


def _import_dependencies() -> tuple[Any, Any]:
    try:
        diffusers = import_module("diffusers")
        torch = import_module("torch")
    except ModuleNotFoundError as exc:
        raise DiffusersDependencyError(_INSTALL_HINT) from exc

    diffusion_pipeline = getattr(diffusers, "DiffusionPipeline", None)
    if diffusion_pipeline is None:
        raise DiffusersDependencyError(
            "Installed diffusers package does not expose DiffusionPipeline. "
            f"{_INSTALL_HINT}"
        )
    return diffusion_pipeline, torch


def _device_for(torch: Any) -> str:
    cuda = getattr(torch, "cuda", None)
    if cuda is not None and cuda.is_available():
        return "cuda"

    backends = getattr(torch, "backends", None)
    mps = getattr(backends, "mps", None) if backends is not None else None
    if mps is not None and mps.is_available():
        return "mps"

    return "cpu"


def _pipeline_for(*, model: str, device: str, diffusion_pipeline: Any) -> Any:
    cache_key = (model, device)
    if cache_key in _PIPELINE_CACHE:
        return _PIPELINE_CACHE[cache_key]

    try:
        pipeline = diffusion_pipeline.from_pretrained(model)
        pipeline.to(device)
    except Exception as exc:  # pragma: no cover - depends on model/runtime internals
        raise DiffusersBackendError(f"Could not load Diffusers model {model!r}: {exc}") from exc

    _PIPELINE_CACHE[cache_key] = pipeline
    return pipeline


def _save_image(image: Any, output_path: Path, output_format: str) -> None:
    save_format = {"jpeg": "JPEG", "png": "PNG", "webp": "WEBP"}[output_format]
    if output_format == "jpeg" and getattr(image, "mode", None) != "RGB":
        image = image.convert("RGB")
    image.save(output_path, format=save_format)

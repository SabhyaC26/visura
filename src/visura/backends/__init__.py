from __future__ import annotations

from visura.backends.base import BackendCapabilities, ImageBackend
from visura.backends.openai import OpenAIBackend

_REGISTRY: dict[str, ImageBackend] = {
    OpenAIBackend.name: OpenAIBackend(),
}


def get_backend(provider: str) -> ImageBackend:
    try:
        return _REGISTRY[provider]
    except KeyError as exc:
        raise KeyError(f"Unknown provider: {provider}") from exc


def registered_backends() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


__all__ = ["BackendCapabilities", "ImageBackend", "get_backend", "registered_backends"]

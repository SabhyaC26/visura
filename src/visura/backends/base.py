from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from visura.kinds.base import PromptPayload
from visura.spec import Spec


@dataclass(frozen=True)
class BackendCapabilities:
    supports_references: bool
    supports_seed: bool
    output_formats: tuple[str, ...]
    sizes: tuple[str, ...] | None = None


class ImageBackend(Protocol):
    name: str
    capabilities: BackendCapabilities

    def validate_options(self, spec: Spec) -> None:
        """Raise ValueError when the spec uses unsupported backend options."""

    def render(self, spec: Spec, payload: PromptPayload, output_path: Path) -> None:
        """Render the compiled payload to output_path."""

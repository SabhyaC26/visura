from __future__ import annotations

import re

from visura.backends.base import BackendCapabilities
from visura.spec import Spec


class BFLBackend:
    name = "bfl"
    models = (
        "flux-2-max",
        "flux-2-pro-preview",
        "flux-2-pro",
        "flux-2-flex",
        "flux-2-klein-4b",
        "flux-2-klein-9b-preview",
        "flux-2-klein-9b",
        "flux-kontext-max",
        "flux-kontext-pro",
        "flux-pro-1.1-ultra",
        "flux-pro-1.1",
        "flux-pro",
        "flux-dev",
    )
    capabilities = BackendCapabilities(
        supports_references=False,
        supports_seed=True,
        output_formats=("png", "jpeg"),
        sizes=None,
    )

    def validate_options(self, spec: Spec) -> None:
        if spec.model not in self.models:
            supported = ", ".join(self.models)
            raise ValueError(
                f"Unsupported model for {self.name}: {spec.model}. Supported: {supported}"
            )
        if spec.output_format not in self.capabilities.output_formats:
            raise ValueError(f"Unsupported output format for {self.name}: {spec.output_format}")
        if spec.references:
            raise ValueError(f"References are not supported by {self.name} text-to-image models")

        width, height = _parse_size(spec.size)
        if width % 16 != 0 or height % 16 != 0:
            raise ValueError(
                f"Unsupported size for {self.name}: dimensions must be multiples of 16"
            )
        if width < 64 or height < 64:
            raise ValueError(f"Unsupported size for {self.name}: dimensions must be at least 64x64")
        if width * height > 4_000_000:
            raise ValueError(
                f"Unsupported size for {self.name}: output must not exceed 4 megapixels"
            )


def _parse_size(size: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d+)x(\d+)", size)
    if match is None:
        raise ValueError(f"Unsupported size for bfl: expected WIDTHxHEIGHT, got {size!r}")
    return int(match.group(1)), int(match.group(2))

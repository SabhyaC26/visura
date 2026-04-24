from __future__ import annotations

from visura.backends.base import BackendCapabilities
from visura.spec import Spec


class OpenAIBackend:
    name = "openai"
    capabilities = BackendCapabilities(
        supports_references=True,
        supports_seed=False,
        output_formats=("png", "jpeg", "webp"),
        sizes=None,
    )

    def validate_options(self, spec: Spec) -> None:
        if spec.output_format not in self.capabilities.output_formats:
            raise ValueError(f"Unsupported output format for {self.name}: {spec.output_format}")

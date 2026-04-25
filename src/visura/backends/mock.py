from __future__ import annotations

import hashlib
import json
import re
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw

from visura.backends.base import BackendCapabilities
from visura.kinds.base import PromptPayload
from visura.spec import Spec


class MockBackend:
    name = "mock"
    capabilities = BackendCapabilities(
        supports_references=True,
        supports_seed=True,
        output_formats=("png", "jpeg", "webp"),
        sizes=None,
    )

    def validate_options(self, spec: Spec) -> None:
        if spec.output_format not in self.capabilities.output_formats:
            raise ValueError(f"Unsupported output format for {self.name}: {spec.output_format}")
        _parse_size(spec.size)

    def render(self, spec: Spec, payload: PromptPayload, output_path: Path) -> None:
        width, height = _parse_size(spec.size)
        digest = _payload_digest(spec, payload)
        background = _color_from_digest(digest, offset=0)
        accent = _color_from_digest(digest, offset=6)

        image = Image.new("RGB", (width, height), background)
        draw = ImageDraw.Draw(image)

        margin = max(24, min(width, height) // 18)
        draw.rectangle(
            (margin, margin, width - margin, height - margin),
            outline=accent,
            width=max(2, min(width, height) // 160),
        )

        lines = [
            "VISURA MOCK RENDER",
            f"kind: {spec.kind}",
            f"output: {spec.output.path}",
            f"size: {spec.size}",
            f"provider: {spec.provider}",
            f"model: {spec.model}",
            f"prompt sha256: {digest[:16]}",
            "",
            payload.prompt[:360],
        ]

        text_width = max(24, (width - margin * 2) // 10)
        wrapped_lines: list[str] = []
        for line in lines:
            wrapped_lines.extend(textwrap.wrap(line, width=text_width) or [""])

        y = margin + 20
        line_height = 18
        for line in wrapped_lines:
            if y + line_height > height - margin:
                break
            draw.text((margin + 20, y), line, fill=(245, 245, 240))
            y += line_height

        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path, format=spec.output_format.upper())


def _parse_size(size: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d+)x(\d+)", size)
    if match is None:
        raise ValueError(f"Unsupported size for mock: expected WIDTHxHEIGHT, got {size!r}")
    return int(match.group(1)), int(match.group(2))


def _payload_digest(spec: Spec, payload: PromptPayload) -> str:
    data = {
        "spec": spec.model_dump(mode="json"),
        "payload": payload.model_dump(mode="json"),
    }
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _color_from_digest(digest: str, *, offset: int) -> tuple[int, int, int]:
    return tuple(
        40 + int(digest[offset + index * 2 : offset + index * 2 + 2], 16) // 2
        for index in range(3)
    )

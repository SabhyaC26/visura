from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from visura.backends.base import BackendCapabilities
from visura.kinds.base import PromptPayload
from visura.spec import Spec


class BFLRenderError(RuntimeError):
    """Raised when BFL rendering fails."""


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

    def render(self, spec: Spec, payload: PromptPayload, output_path: Path) -> None:
        api_key = os.environ.get("BFL_API_KEY")
        if not api_key:
            raise BFLRenderError("BFL_API_KEY is required for provider: bfl")

        width, height = _parse_size(spec.size)
        request_body: dict[str, object] = {
            "prompt": payload.prompt,
            "width": width,
            "height": height,
            "output_format": spec.output_format,
        }
        if spec.seed is not None:
            request_body["seed"] = spec.seed

        generation = _request_json(
            f"https://api.bfl.ai/v1/{spec.model}",
            api_key=api_key,
            method="POST",
            body=request_body,
        )
        polling_url = generation.get("polling_url")
        if not isinstance(polling_url, str) or not polling_url:
            raise BFLRenderError("BFL response did not include polling_url")

        result = _poll_result(polling_url, api_key=api_key)
        sample_url = _sample_url(result)
        image_bytes = _download_bytes(sample_url)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_bytes)


def _parse_size(size: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d+)x(\d+)", size)
    if match is None:
        raise ValueError(f"Unsupported size for bfl: expected WIDTHxHEIGHT, got {size!r}")
    return int(match.group(1)), int(match.group(2))


def _request_json(
    url: str,
    *,
    api_key: str,
    method: str,
    body: dict[str, object] | None = None,
) -> dict[str, object]:
    data = None
    headers = {
        "accept": "application/json",
        "x-key": api_key,
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise BFLRenderError(f"BFL API request failed with HTTP {exc.code}: {detail}") from exc
    except (OSError, URLError, json.JSONDecodeError) as exc:
        raise BFLRenderError(f"BFL API request failed: {exc}") from exc

    if not isinstance(payload, dict):
        raise BFLRenderError("BFL API response was not a JSON object")
    return payload


def _poll_result(polling_url: str, *, api_key: str) -> dict[str, object]:
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        result = _request_json(polling_url, api_key=api_key, method="GET")
        status = result.get("status")
        if status == "Ready":
            return result
        if status in {"Error", "Failed", "Request Moderated", "Content Moderated"}:
            raise BFLRenderError(f"BFL generation failed with status {status}: {result}")
        time.sleep(0.5)

    raise BFLRenderError("Timed out waiting for BFL generation")


def _sample_url(result: dict[str, object]) -> str:
    result_body = result.get("result")
    if not isinstance(result_body, dict):
        raise BFLRenderError("BFL result did not include result object")
    sample = result_body.get("sample")
    if not isinstance(sample, str) or not sample:
        raise BFLRenderError("BFL result did not include result.sample")
    return sample


def _download_bytes(url: str) -> bytes:
    try:
        with urlopen(url, timeout=60) as response:
            return response.read()
    except (OSError, URLError) as exc:
        raise BFLRenderError(f"Could not download BFL result image: {exc}") from exc

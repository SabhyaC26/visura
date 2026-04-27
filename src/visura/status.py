from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from visura.backends import get_backend
from visura.compiler import CompileError, compile_spec
from visura.loader import SpecLoadError, load_spec
from visura.render import (
    CACHE_DIR,
    compute_render_hash,
    file_digest,
    reference_digests_for,
    sidecar_path_for,
)

StatusState = Literal["clean", "invalid", "missing_output", "missing_sidecar", "stale", "changed"]


class AssetStatus(BaseModel):
    spec_path: str
    ok: bool
    state: StatusState
    error: str | None = None
    output_path: str | None = None
    sidecar_path: str | None = None
    provider: str | None = None
    model: str | None = None
    kind: str | None = None
    output_exists: bool = False
    sidecar_exists: bool = False
    cache_exists: bool = False
    current_render_hash: str | None = None
    sidecar_render_hash: str | None = None
    output_digest: str | None = None
    sidecar_output_digest: str | None = None


def collect_spec_paths(paths: list[Path] | None = None) -> list[Path]:
    candidates = paths or [Path.cwd()]
    spec_paths: list[Path] = []
    for candidate in candidates:
        if candidate.is_dir():
            spec_paths.extend(_discover_specs(candidate))
        else:
            spec_paths.append(candidate)
    return sorted(_dedupe(spec_paths), key=lambda path: str(path))


def status_for_path(path: Path) -> AssetStatus:
    try:
        spec = load_spec(path)
        payload = compile_spec(spec)
        backend = get_backend(spec.provider)
    except (SpecLoadError, CompileError, KeyError) as exc:
        return AssetStatus(
            spec_path=str(path),
            ok=False,
            state="invalid",
            error=str(exc),
        )

    output_path = Path(spec.output.path)
    sidecar_path = sidecar_path_for(output_path)
    reference_digests = reference_digests_for(spec)
    current_render_hash = compute_render_hash(
        spec=spec,
        payload=payload,
        backend=backend,
        reference_digests=reference_digests,
    )
    cache_path = cache_path_for(current_render_hash, spec.output_format)

    output_exists = output_path.exists()
    sidecar_exists = sidecar_path.exists()
    output_digest = file_digest(output_path) if output_exists else None
    sidecar_render_hash = None
    sidecar_output_digest = None

    if sidecar_exists:
        sidecar = _read_sidecar(sidecar_path)
        sidecar_render_hash = _string_or_none(sidecar.get("render_hash"))
        sidecar_output_digest = _string_or_none(sidecar.get("output_digest"))

    state: StatusState
    if not output_exists:
        state = "missing_output"
    elif not sidecar_exists:
        state = "missing_sidecar"
    elif sidecar_render_hash != current_render_hash:
        state = "stale"
    elif sidecar_output_digest != output_digest:
        state = "changed"
    else:
        state = "clean"

    return AssetStatus(
        spec_path=str(path),
        ok=state == "clean",
        state=state,
        output_path=str(output_path),
        sidecar_path=str(sidecar_path),
        provider=spec.provider,
        model=spec.model,
        kind=spec.kind,
        output_exists=output_exists,
        sidecar_exists=sidecar_exists,
        cache_exists=cache_path.exists(),
        current_render_hash=current_render_hash,
        sidecar_render_hash=sidecar_render_hash,
        output_digest=output_digest,
        sidecar_output_digest=sidecar_output_digest,
    )


def cache_path_for(render_hash: str, output_format: str) -> Path:
    _, digest = render_hash.split(":", maxsplit=1)
    return CACHE_DIR / f"{digest}.{output_format}"


def _discover_specs(directory: Path) -> list[Path]:
    ignored_parts = {".git", ".venv", "__pycache__", ".pytest_cache"}
    return [
        path
        for path in directory.rglob("*.visura.toml")
        if not any(part in ignored_parts for part in path.parts)
    ]


def _dedupe(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    deduped: list[Path] = []
    for path in paths:
        normalized = path.resolve() if path.exists() else path
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(path)
    return deduped


def _read_sidecar(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _string_or_none(value: object) -> str | None:
    return value if isinstance(value, str) else None

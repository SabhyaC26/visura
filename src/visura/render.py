from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from visura import __version__
from visura.backends.base import ImageBackend
from visura.kinds.base import PromptPayload
from visura.spec import Spec

CACHE_DIR = Path(".visura/cache")
COMPILER_VERSION = "1"


class ReferenceDigest(BaseModel):
    path: str
    digest: str | None = None
    missing: bool = False


class RenderRecord(BaseModel):
    schema_version: str = "0.1"
    visura_version: str = __version__
    compiler_version: str = COMPILER_VERSION
    backend_version: str
    spec_path: str
    output_path: str
    sidecar_path: str
    provider: str
    model: str
    kind: str
    render_hash: str
    output_digest: str
    cache: Literal["hit", "miss", "refresh"]
    rendered_at: str
    reference_digests: list[ReferenceDigest] = Field(default_factory=list)
    spec: dict[str, Any]
    payload: dict[str, Any]


class RenderResult(BaseModel):
    spec_path: str
    output_path: str
    sidecar_path: str
    provider: str
    model: str
    kind: str
    render_hash: str
    output_digest: str
    cache: Literal["hit", "miss", "refresh"]


def render_with_cache(
    *,
    spec_path: Path,
    spec: Spec,
    payload: PromptPayload,
    backend: ImageBackend,
    output_path: Path,
    force: bool = False,
) -> RenderResult:
    reference_digests = _reference_digests(spec)
    render_hash = compute_render_hash(
        spec=spec,
        payload=payload,
        backend=backend,
        reference_digests=reference_digests,
    )
    cache_path = _cache_path(render_hash, spec.output_format)
    sidecar_path = sidecar_path_for(output_path)

    if cache_path.exists() and not force:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cache_path, output_path)
        cache_status: Literal["hit", "miss", "refresh"] = "hit"
    else:
        backend.render(spec, payload, output_path)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(output_path, cache_path)
        cache_status = "refresh" if force else "miss"

    output_digest = file_digest(output_path)
    record = RenderRecord(
        backend_version=_backend_version(backend),
        spec_path=str(spec_path),
        output_path=str(output_path),
        sidecar_path=str(sidecar_path),
        provider=spec.provider,
        model=spec.model,
        kind=spec.kind,
        render_hash=render_hash,
        output_digest=output_digest,
        cache=cache_status,
        rendered_at=datetime.now(UTC).isoformat(),
        reference_digests=reference_digests,
        spec=spec.model_dump(mode="json"),
        payload=payload.model_dump(mode="json"),
    )
    write_sidecar(sidecar_path, record)

    return RenderResult(
        spec_path=str(spec_path),
        output_path=str(output_path),
        sidecar_path=str(sidecar_path),
        provider=spec.provider,
        model=spec.model,
        kind=spec.kind,
        render_hash=render_hash,
        output_digest=output_digest,
        cache=cache_status,
    )


def compute_render_hash(
    *,
    spec: Spec,
    payload: PromptPayload,
    backend: ImageBackend,
    reference_digests: list[ReferenceDigest] | None = None,
) -> str:
    data = {
        "backend": {
            "name": backend.name,
            "version": _backend_version(backend),
        },
        "compiler_version": COMPILER_VERSION,
        "references": [
            reference.model_dump(mode="json") for reference in (reference_digests or [])
        ],
        "spec": spec.model_dump(mode="json"),
        "payload": payload.model_dump(mode="json"),
        "visura_version": __version__,
    }
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def sidecar_path_for(output_path: Path) -> Path:
    return output_path.with_suffix(".visura.json")


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def write_sidecar(path: Path, record: RenderRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(record.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _reference_digests(spec: Spec) -> list[ReferenceDigest]:
    digests: list[ReferenceDigest] = []
    for reference in spec.references:
        path = reference.path
        if path.exists():
            digests.append(ReferenceDigest(path=str(path), digest=file_digest(path)))
        else:
            digests.append(ReferenceDigest(path=str(path), missing=True))
    return digests


def _cache_path(render_hash: str, output_format: str) -> Path:
    _, digest = render_hash.split(":", maxsplit=1)
    return CACHE_DIR / f"{digest}.{output_format}"


def _backend_version(backend: ImageBackend) -> str:
    return getattr(backend, "version", "1")

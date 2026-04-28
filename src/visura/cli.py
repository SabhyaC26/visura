from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import typer
from pydantic import BaseModel

from visura import __version__
from visura.backends import get_backend
from visura.backends.bfl import BFLRenderError
from visura.compiler import CompileError, compile_spec
from visura.loader import SpecLoadError, load_spec
from visura.render import (
    compute_render_hash,
    reference_digests_for,
    render_with_cache,
    sidecar_path_for,
)
from visura.spec import Spec
from visura.status import cache_path_for, collect_spec_paths, status_for_path

app = typer.Typer(no_args_is_help=True, add_completion=False)
STATUS_PATHS_ARGUMENT = typer.Argument(
    None,
    help="Spec files or directories to inspect. Defaults to the current directory.",
)
RENDER_PATHS_ARGUMENT = typer.Argument(
    ...,
    help="Spec files, directories, or globs to render.",
)
JSON_OPTION = typer.Option(
    False,
    "--json",
    help="Emit JSON output. This is currently the default.",
)
ProviderAction = Literal["render", "refresh", "restore_from_cache"]
CacheState = Literal["hit", "miss", "refresh"]


class RenderCommandResult(BaseModel):
    spec_path: str
    ok: bool
    error: str | None = None
    output_path: str | None = None
    sidecar_path: str | None = None
    provider: str | None = None
    model: str | None = None
    kind: str | None = None
    render_hash: str | None = None
    output_digest: str | None = None
    cache: CacheState | None = None
    planned_action: ProviderAction | None = None
    dry_run: bool = False


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        help="Show the Visura version and exit.",
        is_eager=True,
    ),
) -> None:
    """Declarative image generation specs."""


@app.command()
def validate(
    path: Path,
    json_output: bool = JSON_OPTION,
) -> None:
    """Validate and print the resolved spec."""
    try:
        spec = load_spec(path)
    except SpecLoadError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    typer.echo(json.dumps(spec.model_dump(mode="json"), indent=2, sort_keys=True))


@app.command()
def compile(
    path: Path,
    provider: str | None = typer.Option(
        None,
        "--provider",
        help="Override the spec provider for this compile.",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help="Override the spec model for this compile.",
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Compile a spec into an inspectable prompt payload."""
    try:
        spec = _load_spec(path, provider_override=provider, model_override=model)
        payload = compile_spec(spec)
    except (SpecLoadError, CompileError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    typer.echo(json.dumps(payload.model_dump(mode="json"), indent=2, sort_keys=True))


@app.command()
def render(
    paths: list[Path] = RENDER_PATHS_ARGUMENT,
    yes: bool = typer.Option(
        False,
        "--yes",
        help="Allow rendering with paid or networked providers.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Bypass the render cache and refresh the cached artifact.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Print planned render actions without writing outputs, sidecars, or cache files.",
    ),
    provider: str | None = typer.Option(
        None,
        "--provider",
        help="Override the spec provider for this render.",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help="Override the spec model for this render.",
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Render a spec with a supported local backend."""
    spec_paths = collect_spec_paths(paths)
    if not spec_paths:
        typer.echo("[]")
        typer.echo("No Visura specs found.", err=True)
        raise typer.Exit(1)

    results = [
        _render_one(
            path=path,
            yes=yes,
            force=force,
            dry_run=dry_run,
            provider_override=provider,
            model_override=model,
        )
        for path in spec_paths
    ]

    output: dict[str, object] | list[dict[str, object]]
    payloads = [result.model_dump(mode="json") for result in results]
    output = payloads[0] if len(payloads) == 1 else payloads
    typer.echo(json.dumps(output, indent=2, sort_keys=True))

    failures = [result for result in results if not result.ok]
    for failure in failures:
        if failure.error is not None:
            typer.echo(failure.error, err=True)
    if failures:
        raise typer.Exit(1)


@app.command()
def status(
    paths: list[Path] | None = STATUS_PATHS_ARGUMENT,
    json_output: bool = JSON_OPTION,
) -> None:
    """Inspect specs, outputs, sidecars, and render cache state."""
    results = [status_for_path(path) for path in collect_spec_paths(paths)]
    typer.echo(
        json.dumps(
            [result.model_dump(mode="json") for result in results],
            indent=2,
            sort_keys=True,
        )
    )
    if any(not result.ok for result in results):
        raise typer.Exit(1)


def _load_spec(
    path: Path,
    *,
    provider_override: str | None = None,
    model_override: str | None = None,
) -> Spec:
    spec = load_spec(path)
    updates: dict[str, str] = {}
    if provider_override is not None:
        updates["provider"] = _non_blank_override(provider_override, "provider")
    if model_override is not None:
        updates["model"] = _non_blank_override(model_override, "model")
    return spec.model_copy(update=updates) if updates else spec


def _render_one(
    *,
    path: Path,
    yes: bool,
    force: bool,
    dry_run: bool,
    provider_override: str | None,
    model_override: str | None,
) -> RenderCommandResult:
    try:
        spec = _load_spec(
            path,
            provider_override=provider_override,
            model_override=model_override,
        )
        output_path = Path(spec.output.path)
        sidecar_path = sidecar_path_for(output_path)
        backend = get_backend(spec.provider)
    except (SpecLoadError, KeyError, ValueError) as exc:
        return RenderCommandResult(
            spec_path=str(path),
            ok=False,
            error=str(exc),
        )

    base = {
        "spec_path": str(path),
        "output_path": str(output_path),
        "sidecar_path": str(sidecar_path),
        "provider": spec.provider,
        "model": spec.model,
        "kind": spec.kind,
        "dry_run": dry_run,
    }

    if spec.provider != "mock" and not yes:
        return RenderCommandResult(
            **base,
            ok=False,
            error="Rendering with paid or networked providers requires --yes.",
        )

    try:
        payload = compile_spec(spec)
    except CompileError as exc:
        return RenderCommandResult(
            **base,
            ok=False,
            error=str(exc),
        )

    if dry_run:
        return _plan_render(
            path=path,
            spec=spec,
            payload=payload,
            backend=backend,
            output_path=output_path,
            sidecar_path=sidecar_path,
            force=force,
        )

    if not callable(getattr(backend, "render", None)):
        return RenderCommandResult(
            **base,
            ok=False,
            error=f"Provider does not support CLI rendering: {spec.provider}",
        )

    try:
        result = render_with_cache(
            spec_path=path,
            spec=spec,
            payload=payload,
            backend=backend,
            output_path=output_path,
            force=force,
        )
    except (BFLRenderError, ValueError, OSError) as exc:
        return RenderCommandResult(
            **base,
            ok=False,
            error=str(exc),
        )

    return RenderCommandResult(
        **result.model_dump(mode="json"),
        ok=True,
        planned_action=_planned_action_for(result.cache),
        dry_run=False,
    )


def _plan_render(
    *,
    path: Path,
    spec: Spec,
    payload: object,
    backend: object,
    output_path: Path,
    sidecar_path: Path,
    force: bool,
) -> RenderCommandResult:
    reference_digests = reference_digests_for(spec)
    render_hash = compute_render_hash(
        spec=spec,
        payload=payload,
        backend=backend,
        reference_digests=reference_digests,
    )
    cache = _cache_state_for(render_hash, spec.output_format, force=force)
    return RenderCommandResult(
        spec_path=str(path),
        ok=True,
        output_path=str(output_path),
        sidecar_path=str(sidecar_path),
        provider=spec.provider,
        model=spec.model,
        kind=spec.kind,
        render_hash=render_hash,
        cache=cache,
        planned_action=_planned_action_for(cache),
        dry_run=True,
    )


def _cache_state_for(render_hash: str, output_format: str, *, force: bool) -> CacheState:
    if force:
        return "refresh"
    return "hit" if cache_path_for(render_hash, output_format).exists() else "miss"


def _planned_action_for(cache: CacheState) -> ProviderAction:
    if cache == "hit":
        return "restore_from_cache"
    if cache == "refresh":
        return "refresh"
    return "render"


def _non_blank_override(value: str, name: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{name} override must not be blank")
    return stripped

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import typer
from pydantic import BaseModel, Field

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
    help="Emit JSON output. JSON is the default; this flag is accepted for explicit callers.",
)
QUIET_OPTION = typer.Option(
    False,
    "--quiet",
    help="Suppress human-readable stderr summaries.",
)
CLI_SCHEMA_VERSION = "0.1"
ProviderAction = Literal["render", "refresh", "restore_from_cache"]
CacheState = Literal["hit", "miss", "refresh"]


class RenderCommandResult(BaseModel):
    spec_path: str
    ok: bool
    error: str | None = None
    error_code: str | None = None
    error_field: str | None = None
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


class CliError(BaseModel):
    code: str
    message: str
    path: str | None = None
    field: str | None = None


class CommandResponse(BaseModel):
    schema_version: str = CLI_SCHEMA_VERSION
    command: str
    ok: bool
    results: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[CliError] = Field(default_factory=list)


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
    quiet: bool = QUIET_OPTION,
) -> None:
    """Validate and print the resolved spec."""
    try:
        spec = load_spec(path)
    except SpecLoadError as exc:
        errors = _errors_from_exception(exc, path=path)
        _emit_response("validate", [], errors=errors, quiet=quiet)
        raise typer.Exit(1) from exc

    _emit_response("validate", [spec.model_dump(mode="json")], quiet=quiet)


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
    quiet: bool = QUIET_OPTION,
) -> None:
    """Compile a spec into an inspectable prompt payload."""
    try:
        spec = _load_spec(path, provider_override=provider, model_override=model)
        payload = compile_spec(spec)
    except (SpecLoadError, CompileError, ValueError) as exc:
        errors = _errors_from_exception(exc, path=path)
        _emit_response("compile", [], errors=errors, quiet=quiet)
        raise typer.Exit(1) from exc

    _emit_response("compile", [payload.model_dump(mode="json")], quiet=quiet)


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
    quiet: bool = QUIET_OPTION,
) -> None:
    """Render a spec with a supported local backend."""
    spec_paths = collect_spec_paths(paths)
    if not spec_paths:
        errors = [CliError(code="no_specs_found", message="No Visura specs found.")]
        _emit_response("render", [], errors=errors, quiet=quiet)
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

    payloads = [result.model_dump(mode="json") for result in results]
    failures = [result for result in results if not result.ok]
    errors = [_error_from_render_result(failure) for failure in failures]
    _emit_response("render", payloads, errors=errors, quiet=quiet)
    if failures:
        raise typer.Exit(1)


@app.command()
def status(
    paths: list[Path] | None = STATUS_PATHS_ARGUMENT,
    json_output: bool = JSON_OPTION,
    quiet: bool = QUIET_OPTION,
) -> None:
    """Inspect specs, outputs, sidecars, and render cache state."""
    results = [status_for_path(path) for path in collect_spec_paths(paths)]
    payloads = [result.model_dump(mode="json") for result in results]
    errors = [_error_from_status_result(result) for result in results if not result.ok]
    _emit_response("status", payloads, errors=errors, quiet=quiet)
    if any(not result.ok for result in results):
        raise typer.Exit(1)


def _emit_response(
    command: str,
    results: list[dict[str, Any]],
    *,
    errors: list[CliError] | None = None,
    quiet: bool,
) -> None:
    response = CommandResponse(
        command=command,
        ok=not errors,
        results=results,
        errors=errors or [],
    )
    typer.echo(json.dumps(response.model_dump(mode="json"), indent=2, sort_keys=True))
    if quiet:
        return
    for error in response.errors:
        typer.echo(_format_cli_error(error), err=True)


def _errors_from_exception(exc: Exception, *, path: Path | None = None) -> list[CliError]:
    if isinstance(exc, SpecLoadError):
        error_path = str(exc.path or path) if (exc.path or path) is not None else None
        if exc.issues:
            return [
                CliError(
                    code=exc.code,
                    message=issue.message,
                    path=error_path,
                    field=issue.field,
                )
                for issue in exc.issues
            ]
        return [CliError(code=exc.code, message=str(exc), path=error_path)]
    if isinstance(exc, CompileError):
        return [CliError(code="compile_error", message=str(exc), path=str(path) if path else None)]
    if isinstance(exc, ValueError):
        return [
            CliError(
                code="invalid_argument",
                message=str(exc),
                path=str(path) if path else None,
            )
        ]
    return [CliError(code="error", message=str(exc), path=str(path) if path else None)]


def _error_from_render_result(result: RenderCommandResult) -> CliError:
    return CliError(
        code=result.error_code or _render_error_code(result),
        message=result.error or "Render failed.",
        path=result.spec_path,
        field=result.error_field,
    )


def _error_from_status_result(result: object) -> CliError:
    error = getattr(result, "error", None)
    error_code = getattr(result, "error_code", None)
    error_field = getattr(result, "error_field", None)
    state = getattr(result, "state", "status_error")
    return CliError(
        code=error_code or f"status_{state}",
        message=error or f"Asset status is {state}.",
        path=getattr(result, "spec_path", None),
        field=error_field,
    )


def _render_error_code(result: RenderCommandResult) -> str:
    message = result.error or ""
    if "requires --yes" in message:
        return "provider_requires_approval"
    if "does not support CLI rendering" in message:
        return "provider_render_unsupported"
    if "Could not read" in message:
        return "spec_read_error"
    if "Malformed TOML" in message:
        return "spec_toml_error"
    if "Invalid Visura spec" in message:
        return "spec_validation_error"
    if "Unknown kind" in message:
        return "compile_error"
    return "render_error"


def _format_cli_error(error: CliError) -> str:
    location = error.path or "<unknown>"
    if error.field:
        location = f"{location}:{error.field}"
    return f"{error.code}: {location}: {error.message}"


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
        structured_error = _errors_from_exception(exc, path=path)[0]
        return RenderCommandResult(
            spec_path=str(path),
            ok=False,
            error=str(exc),
            error_code=structured_error.code,
            error_field=structured_error.field,
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
            error_code="provider_requires_approval",
        )

    try:
        payload = compile_spec(spec)
    except CompileError as exc:
        return RenderCommandResult(
            **base,
            ok=False,
            error=str(exc),
            error_code="compile_error",
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
            error_code="provider_render_unsupported",
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
            error_code="render_error",
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

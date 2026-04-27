from __future__ import annotations

import json
from pathlib import Path

import typer

from visura import __version__
from visura.backends import get_backend
from visura.backends.bfl import BFLRenderError
from visura.compiler import CompileError, compile_spec
from visura.loader import SpecLoadError, load_spec
from visura.render import render_with_cache
from visura.status import collect_spec_paths, status_for_path

app = typer.Typer(no_args_is_help=True, add_completion=False)
STATUS_PATHS_ARGUMENT = typer.Argument(
    None,
    help="Spec files or directories to inspect. Defaults to the current directory.",
)


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
def validate(path: Path) -> None:
    """Validate and print the resolved spec."""
    try:
        spec = load_spec(path)
    except SpecLoadError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    typer.echo(json.dumps(spec.model_dump(mode="json"), indent=2, sort_keys=True))


@app.command()
def compile(path: Path) -> None:
    """Compile a spec into an inspectable prompt payload."""
    try:
        spec = load_spec(path)
        payload = compile_spec(spec)
    except (SpecLoadError, CompileError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    typer.echo(json.dumps(payload.model_dump(mode="json"), indent=2, sort_keys=True))


@app.command()
def render(
    path: Path,
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
) -> None:
    """Render a spec with a supported local backend."""
    try:
        spec = load_spec(path)
        payload = compile_spec(spec)
        backend = get_backend(spec.provider)
    except (SpecLoadError, CompileError, KeyError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    if spec.provider != "mock" and not yes:
        typer.echo(
            "Rendering with paid or networked providers requires --yes.",
            err=True,
        )
        raise typer.Exit(1)

    output_path = Path(spec.output.path)
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
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    typer.echo(json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True))


@app.command()
def status(
    paths: list[Path] | None = STATUS_PATHS_ARGUMENT,
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

from __future__ import annotations

import json
from pathlib import Path

import typer

from visura import __version__
from visura.loader import SpecLoadError, load_spec

app = typer.Typer(no_args_is_help=True, add_completion=False)


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

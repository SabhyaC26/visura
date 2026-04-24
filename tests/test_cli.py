from __future__ import annotations

from typer.testing import CliRunner

from visura.cli import app


def test_validate_example() -> None:
    result = CliRunner().invoke(app, ["validate", "examples/my-headshot.visura.toml"])

    assert result.exit_code == 0
    assert '"kind": "headshot"' in result.stdout


def test_version() -> None:
    result = CliRunner().invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip()

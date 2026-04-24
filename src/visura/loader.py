from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import ValidationError

from visura.spec import Spec


class SpecLoadError(Exception):
    """Raised when a Visura spec cannot be parsed or validated."""


def load_spec(path: str | Path) -> Spec:
    spec_path = Path(path)
    try:
        raw = tomllib.loads(spec_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SpecLoadError(f"Could not read {spec_path}: {exc.strerror}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise SpecLoadError(f"Malformed TOML in {spec_path}: {exc}") from exc

    try:
        return Spec.model_validate(raw)
    except ValidationError as exc:
        raise SpecLoadError(_format_validation_error(spec_path, exc)) from exc


def _format_validation_error(path: Path, error: ValidationError) -> str:
    lines = [f"Invalid Visura spec: {path}"]
    for issue in error.errors():
        location = ".".join(str(part) for part in issue["loc"]) or "<root>"
        lines.append(f"- {location}: {issue['msg']}")
    return "\n".join(lines)

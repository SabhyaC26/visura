from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import ValidationError

from visura.spec import Spec


class SpecLoadIssue:
    def __init__(self, *, message: str, field: str | None = None) -> None:
        self.message = message
        self.field = field


class SpecLoadError(Exception):
    """Raised when a Visura spec cannot be parsed or validated."""

    def __init__(
        self,
        message: str,
        *,
        path: Path | None = None,
        code: str = "spec_load_error",
        issues: list[SpecLoadIssue] | None = None,
    ) -> None:
        super().__init__(message)
        self.path = path
        self.code = code
        self.issues = issues or []


def load_spec(path: str | Path) -> Spec:
    spec_path = Path(path)
    try:
        raw = tomllib.loads(spec_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SpecLoadError(
            f"Could not read {spec_path}: {exc.strerror}",
            path=spec_path,
            code="spec_read_error",
        ) from exc
    except tomllib.TOMLDecodeError as exc:
        raise SpecLoadError(
            f"Malformed TOML in {spec_path}: {exc}",
            path=spec_path,
            code="spec_toml_error",
        ) from exc

    try:
        return Spec.model_validate(raw)
    except ValidationError as exc:
        raise SpecLoadError(
            _format_validation_error(spec_path, exc),
            path=spec_path,
            code="spec_validation_error",
            issues=_validation_issues(exc),
        ) from exc


def _format_validation_error(path: Path, error: ValidationError) -> str:
    lines = [f"Invalid Visura spec: {path}"]
    for issue in error.errors():
        location = ".".join(str(part) for part in issue["loc"]) or "<root>"
        lines.append(f"- {location}: {issue['msg']}")
    return "\n".join(lines)


def _validation_issues(error: ValidationError) -> list[SpecLoadIssue]:
    issues: list[SpecLoadIssue] = []
    for issue in error.errors():
        location = ".".join(str(part) for part in issue["loc"]) or "<root>"
        issues.append(SpecLoadIssue(message=issue["msg"], field=location))
    return issues

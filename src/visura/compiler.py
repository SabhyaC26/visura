from __future__ import annotations

from visura.backends import get_backend
from visura.kinds import get as get_kind_compiler
from visura.kinds.base import PromptPayload
from visura.spec import Spec


class CompileError(Exception):
    """Raised when a Visura spec cannot be compiled."""


def compile_spec(spec: Spec) -> PromptPayload:
    try:
        backend = get_backend(spec.provider)
        backend.validate_options(spec)
        compiler = get_kind_compiler(spec.kind)
        return compiler(spec)
    except (KeyError, ValueError) as exc:
        raise CompileError(str(exc)) from exc

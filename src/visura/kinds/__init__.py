from __future__ import annotations

from collections.abc import Callable

from visura.spec import Spec

from .base import PromptPayload

KindCompiler = Callable[[Spec], PromptPayload]

_REGISTRY: dict[str, KindCompiler] = {}


def register(name: str) -> Callable[[KindCompiler], KindCompiler]:
    def decorator(compiler: KindCompiler) -> KindCompiler:
        if name in _REGISTRY:
            raise ValueError(f"Kind already registered: {name}")
        _REGISTRY[name] = compiler
        return compiler

    return decorator


def get(name: str) -> KindCompiler:
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise KeyError(f"Unknown kind: {name}") from exc


def registered_kinds() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


from visura.kinds import builtin as _builtin  # noqa: E402, F401

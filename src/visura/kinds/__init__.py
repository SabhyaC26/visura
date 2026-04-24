from __future__ import annotations

from collections.abc import Callable
from typing import Any

KindCompiler = Callable[[Any, dict[str, Any]], Any]

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

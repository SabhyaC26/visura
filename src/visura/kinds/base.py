from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PromptPayload:
    prompt: str
    options: dict[str, Any] = field(default_factory=dict)

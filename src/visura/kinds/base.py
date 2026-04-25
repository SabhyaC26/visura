from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PromptReference(BaseModel):
    path: str
    role: str
    prompt: str | None = None


class PromptOutput(BaseModel):
    path: str
    alt: str
    name: str | None = None


class PromptPayload(BaseModel):
    kind: str
    provider: str
    model: str
    prompt: str
    negative_prompt: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)
    references: list[PromptReference] = Field(default_factory=list)
    output: PromptOutput

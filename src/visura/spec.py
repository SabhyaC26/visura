from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

OutputFormat = Literal["png", "jpeg", "webp"]


class Style(BaseModel):
    model_config = ConfigDict(extra="forbid")

    medium: str | None = None
    mood: str | None = None
    palette: list[str] = Field(default_factory=list)
    notes: str | None = None


class Reference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: Path
    role: str = "reference"
    prompt: str | None = None

    @field_validator("role")
    @classmethod
    def role_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("role must not be blank")
        return value


class Spec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str
    model: str
    provider: str = "openai"
    size: str = "1024x1024"
    seed: int | None = None
    quality: str | None = None
    output_format: OutputFormat = "png"
    background: str | None = None
    style: Style = Field(default_factory=Style)
    references: list[Reference] = Field(default_factory=list)
    content: dict[str, Any]

    @field_validator("kind", "model", "provider", "size")
    @classmethod
    def required_strings_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from visura.kinds import register
from visura.kinds.base import PromptOutput, PromptPayload, PromptReference
from visura.spec import Spec


class KindCompileError(ValueError):
    """Raised when kind-specific content cannot be compiled."""


def _require_content(spec: Spec, fields: Iterable[str]) -> None:
    missing = [
        field
        for field in fields
        if field not in spec.content or not str(spec.content[field]).strip()
    ]
    if missing:
        joined = ", ".join(missing)
        raise KindCompileError(f"{spec.kind} content is missing required field(s): {joined}")


def _format_value(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def _article_for(phrase: str) -> str:
    return "an" if phrase[:1].lower() in {"a", "e", "i", "o", "u"} else "a"


def _prompt_for(spec: Spec, *, required: Iterable[str]) -> PromptPayload:
    _require_content(spec, required)

    kind_label = spec.kind.replace("_", " ")
    parts = [f"Create {_article_for(kind_label)} {kind_label} image."]
    if spec.style.medium:
        parts.append(f"Medium: {spec.style.medium}.")
    if spec.style.mood:
        parts.append(f"Mood: {spec.style.mood}.")
    if spec.style.palette:
        parts.append(f"Palette: {', '.join(spec.style.palette)}.")
    if spec.style.notes:
        parts.append(f"Style notes: {spec.style.notes}")
    if spec.background:
        parts.append(f"Background: {spec.background}.")

    for key in spec.content:
        parts.append(f"{key.replace('_', ' ').title()}: {_format_value(spec.content[key])}.")

    options: dict[str, Any] = {
        "size": spec.size,
        "output_format": spec.output_format,
    }
    if spec.quality is not None:
        options["quality"] = spec.quality
    if spec.seed is not None:
        options["seed"] = spec.seed
    if spec.background is not None:
        options["background"] = spec.background

    return PromptPayload(
        kind=spec.kind,
        provider=spec.provider,
        model=spec.model,
        prompt=" ".join(parts),
        options=options,
        references=[
            PromptReference(
                path=str(reference.path),
                role=reference.role,
                prompt=reference.prompt,
            )
            for reference in spec.references
        ],
        output=PromptOutput(
            path=str(spec.output.path),
            alt=spec.output.alt,
            name=spec.output.name,
        ),
    )


@register("blueprint")
def compile_blueprint(spec: Spec) -> PromptPayload:
    return _prompt_for(spec, required=("object",))


@register("comic_panel")
def compile_comic_panel(spec: Spec) -> PromptPayload:
    return _prompt_for(spec, required=("scene",))


@register("headshot")
def compile_headshot(spec: Spec) -> PromptPayload:
    return _prompt_for(spec, required=("subject",))


@register("anime_character")
def compile_anime_character(spec: Spec) -> PromptPayload:
    return _prompt_for(spec, required=("character",))


@register("infographic")
def compile_infographic(spec: Spec) -> PromptPayload:
    return _prompt_for(spec, required=("title",))


@register("poster")
def compile_poster(spec: Spec) -> PromptPayload:
    return _prompt_for(spec, required=("headline",))


@register("product_mockup")
def compile_product_mockup(spec: Spec) -> PromptPayload:
    return _prompt_for(spec, required=("product",))

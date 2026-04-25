# Visura

Visura is a Python library and CLI for declarative, replayable image generation
specs. Instead of keeping one-off prose prompts in notes or chat history, you
write a small `.visura.toml` file that captures the image intent, model options,
style guidance, references, and structured content in a format that can be
validated, versioned, reviewed, and eventually rendered.

The current v0 surface is intentionally small: Visura validates specs and prints
the resolved JSON representation. Rendering, prompt compilation, sidecar
metadata, and artifact caching are planned next.

## Why Visura?

Image generation work often starts as a prompt, then quickly turns into a set of
model choices, image dimensions, style constraints, reference images, and
iteration notes. Visura makes that state explicit:

- Specs are plain TOML, so they are easy to read and commit.
- Validation catches unknown fields, missing fields, wrong types, and malformed
  TOML before you spend time or API calls.
- Provider and model controls live next to the content that depends on them.
- The format is designed for replayability: future render output can be tied
  back to the exact spec that produced it.

## Project Status

Implemented today:

- `.visura.toml` loading via Python's `tomllib`
- Pydantic validation for the v0 spec envelope
- `visura validate <path>` CLI command
- Example specs for headshots, product mockups, posters, blueprints, and
  infographics
- OpenAI and Black Forest Labs backend capability scaffolds

Not implemented yet:

- `visura render`
- `visura compile`
- Provider API calls
- Cache restoration and render sidecar metadata
- Kind-specific compilers

## Requirements

- Python 3.11+
- `uv` for the recommended development workflow

Runtime dependencies are declared in `pyproject.toml`:

- `pydantic`
- `typer`
- `openai`
- `pillow`

## Install

From a local checkout:

```bash
git clone <repo-url>
cd visura
uv sync
```

You can also install the package into another environment in editable mode:

```bash
python -m pip install -e .
```

## How To Run

Show CLI help:

```bash
uv run visura --help
```

Show the installed package version:

```bash
uv run visura --version
```

Validate one spec:

```bash
uv run visura validate examples/my-headshot.visura.toml
```

Validate every checked-in example:

```bash
for spec in examples/*.visura.toml; do
  uv run visura validate "$spec" >/dev/null
  echo "ok: $spec"
done
```

The validate command prints the resolved spec as formatted JSON. For example:

```json
{
  "background": null,
  "content": {
    "background": "clean charcoal studio backdrop",
    "expression": "friendly half-smile",
    "lighting": "large softbox key light with subtle rim light",
    "pose": "three-quarter view, relaxed shoulders",
    "subject": "Sabhya, a software builder"
  },
  "kind": "headshot",
  "model": "gpt-image-1",
  "output_format": "png",
  "provider": "openai",
  "quality": "high",
  "references": [],
  "seed": null,
  "size": "1024x1024",
  "style": {
    "medium": "editorial studio portrait",
    "mood": "confident, warm, polished",
    "notes": null,
    "palette": [
      "charcoal",
      "warm ivory",
      "soft gold"
    ]
  }
}
```

## Spec Format

A Visura spec is a TOML file with a small top-level envelope plus structured
content:

```toml
kind = "headshot"
provider = "openai"
model = "gpt-image-1"
size = "1024x1024"
quality = "high"
output_format = "png"

[style]
medium = "editorial studio portrait"
mood = "confident, warm, polished"
palette = ["charcoal", "warm ivory", "soft gold"]

[content]
subject = "Sabhya, a software builder"
pose = "three-quarter view, relaxed shoulders"
expression = "friendly half-smile"
background = "clean charcoal studio backdrop"
lighting = "large softbox key light with subtle rim light"
```

Supported top-level fields:

- `kind` - required string. Names the type of image spec, such as `headshot` or
  `infographic`.
- `model` - required string. The provider model name.
- `provider` - optional string, defaults to `openai`. Registered providers are
  `openai` and `bfl`.
- `size` - optional string, defaults to `1024x1024`.
- `seed` - optional integer.
- `quality` - optional string.
- `output_format` - optional string, one of `png`, `jpeg`, or `webp`; defaults
  to `png`.
- `background` - optional string.
- `[style]` - optional style guidance with `medium`, `mood`, `palette`, and
  `notes`.
- `[[references]]` - optional reference images with `path`, `role`, and
  `prompt`.
- `[content]` - required table containing kind-specific image content.

Unknown top-level fields and unknown fields inside `style` or `references` are
rejected so typos fail fast.

### Black Forest Labs

Use `provider = "bfl"` for Black Forest Labs FLUX models. Model names map to BFL
API endpoint names, so cheap FLUX.2 [klein] iteration can use
`model = "flux-2-klein-4b"` or `model = "flux-2-klein-9b-preview"`.

```toml
kind = "product_mockup"
provider = "bfl"
model = "flux-2-klein-4b"
size = "1024x1024"
seed = 1234
output_format = "png"

[content]
product = "a compact desk lamp with brushed aluminum joints"
scene = "on a walnut desk beside a notebook and matte black pen"
lighting = "soft afternoon window light"
```

BFL text-to-image sizes must be `WIDTHxHEIGHT`, use dimensions that are
multiples of 16, and stay within the documented 64x64 minimum and 4 megapixel
maximum. BFL currently accepts `png` and `jpeg` output formats in Visura.

## Examples

### Product Mockup

```toml
kind = "product_mockup"
provider = "openai"
model = "gpt-image-1"
size = "1024x1024"
quality = "high"
output_format = "png"

[style]
medium = "premium product photography"
mood = "bright, tactile, modern"
palette = ["forest green", "cream", "copper"]

[content]
product = "stand-up pouch for a small-batch coffee brand named Northstar"
surface = "matte pouch with a small copper label and simple star mark"
scene = "on a stone counter beside a ceramic cup and scattered coffee beans"
lighting = "soft morning window light with crisp but natural shadows"
```

Run it:

```bash
uv run visura validate examples/coffee-packaging-mockup.visura.toml
```

### Infographic

```toml
kind = "infographic"
provider = "openai"
model = "gpt-image-1"
size = "1024x1536"
quality = "high"
output_format = "png"
background = "opaque"

[style]
medium = "editorial business infographic"
mood = "clear, energetic, credible"
palette = ["ink black", "electric blue", "mint", "warm gray"]

[content]
title = "Launch Week Snapshot"
sections = ["12.4k signups", "38% activation", "4.8k images rendered", "92% cache hit rate"]
layout = "vertical poster with four metric blocks and one simple upward trend chart"
constraints = "large readable numbers, minimal copy, no fake logos, clean grid"
```

Run it:

```bash
uv run visura validate examples/launch-metrics-infographic.visura.toml
```

### Reference Images

References are supported by the schema even though rendering is not wired up yet:

```toml
[[references]]
path = "references/selfie.jpg"
role = "likeness"
prompt = "Use only for facial likeness and hair shape."
```

Reference roles are free-form strings, but they cannot be blank.

## Python API

Load and validate a spec from Python:

```python
from visura import load_spec

spec = load_spec("examples/my-headshot.visura.toml")

print(spec.kind)
print(spec.model)
print(spec.content["subject"])
```

Validation failures raise `visura.loader.SpecLoadError` with a readable message:

```python
from visura.loader import SpecLoadError, load_spec

try:
    spec = load_spec("examples/my-headshot.visura.toml")
except SpecLoadError as exc:
    print(exc)
```

## Development

Install dependencies:

```bash
uv sync
```

Run tests:

```bash
uv run pytest
```

Run linting:

```bash
uv run ruff check .
```

Format code:

```bash
uv run ruff format .
```

Run the CLI directly from the source tree:

```bash
uv run visura validate examples/my-headshot.visura.toml
```

## Repository Layout

```text
src/visura/
  cli.py              Typer CLI entrypoint
  loader.py           TOML parsing and validation
  spec.py             Pydantic models for the v0 spec
  backends/           Backend capability scaffolding
  kinds/              Future kind registry and compilers
examples/             Example .visura.toml files
tests/                Loader and CLI tests
```

## Roadmap

The next major pieces are:

1. Compile structured specs into provider-ready prompt payloads.
2. Add `visura render <spec>` with OpenAI image generation.
3. Write sidecar metadata next to each render.
4. Add content-addressable artifact caching for replayability.
5. Add kind-specific content schemas and compilers.

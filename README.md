# Visura

Visura is a Python library and CLI for declarative, replayable image generation
specs. Instead of leaving prompts in notes, chat history, or one-off scripts,
you write a `.visura.toml` file that captures the image intent, model options,
style guidance, references, output path, and structured content.

The current product is local-first: validate and compile specs, render
deterministic local mock images, cache unchanged outputs, write sidecar
metadata, and inspect asset status. Black Forest Labs rendering has a networked
provider path behind an API key and `--yes`. OpenAI is scaffold-only for the
current milestone, and Diffusers has a first optional local rendering path.

## Project Status

Implemented today:

- `.visura.toml` loading and Pydantic validation.
- `visura validate <path>` for resolved spec JSON.
- `visura compile <path>` for inspectable prompt payload JSON.
- `visura render <path>` for deterministic local `mock` renders.
- Render cache under `.visura/cache`.
- Sidecar metadata next to outputs, such as `assets/poster.visura.json`.
- `visura status [path ...]` for `clean`, `missing_output`,
  `missing_sidecar`, `stale`, `changed`, and `invalid` states.
- A BFL rendering path for networked, key-gated FLUX renders.
- A Diffusers rendering path for optional local model execution.
- Built-in compilers for `anime_character`, `blueprint`, `comic_panel`,
  `headshot`, `infographic`, `poster`, and `product_mockup`.

Partially implemented:

- CLI JSON output exists by default, and `--json` is accepted, but stable
  versioned response wrappers are still planned.
- `render` has `--dry-run`, `--force`, `--yes`, `--provider`, and `--model`;
  `compile` has provider/model overrides. `--quiet` and a full cross-command
  agent contract are still planned.
- `render` accepts files, directories, and globs, but the next milestone should
  harden batch behavior, response shape, and examples for agent use.

Not implemented yet:

- Production OpenAI rendering.
- Provider reference/image-editing workflows.
- A packaged Visura skill for coding agents.

## Install

Requirements:

- Python 3.11+
- `uv` for the recommended development workflow

From a local checkout:

```bash
git clone <repo-url>
cd visura
uv sync
```

For local Diffusers rendering:

```bash
uv sync --extra diffusers
```

## Quickstart: Local Mock Render

Use the mock provider first. It is deterministic, local, CI-friendly, and does
not require API keys.

```bash
uv run visura validate examples/workshop-poster.visura.toml
uv run visura compile examples/workshop-poster.visura.toml
uv run visura render examples/workshop-poster.visura.toml
uv run visura status examples/workshop-poster.visura.toml
```

The render command writes the requested output, writes a sidecar next to it, and
stores the artifact in `.visura/cache`. Rendering the same unchanged spec again
restores from cache. Use `--force` only when you want to refresh the artifact.

For a write-free preview:

```bash
uv run visura render examples/workshop-poster.visura.toml --dry-run --json
```

To force a safe local provider without editing a production-bound spec:

```bash
uv run visura render examples/my-headshot.visura.toml \
  --provider mock \
  --model placeholder \
  --dry-run \
  --json
```

## Spec Format

A Visura spec is a small TOML envelope plus flexible structured content:

```toml
kind = "poster"
provider = "mock"
model = "placeholder"
size = "1024x1536"
quality = "draft"
output_format = "png"

[output]
path = "assets/examples/workshop-poster.png"
alt = "Risograph-style workshop poster for Prompt Craft Night."

[style]
medium = "risograph event poster"
mood = "hands-on, lively, approachable"
palette = ["tomato red", "deep teal", "warm paper", "black"]

[content]
headline = "Make Images That Listen"
details = "Friday, 7 PM, Studio 12"
visual = "overhead view of hands arranging paper prompt cards around a glowing monitor"
constraints = "clear headline, playful composition, no tiny body copy"
```

Supported top-level fields:

- `kind` - required string, such as `poster`, `headshot`, or `infographic`.
- `model` - required provider model name.
- `provider` - optional string, defaults to `openai`; use `mock` for local
  development or `diffusers` for local model rendering.
- `size` - optional string, defaults to `1024x1024`.
- `seed` - optional integer.
- `quality` - optional string.
- `output_format` - optional string, one of `png`, `jpeg`, or `webp`.
- `background` - optional string.
- `[output]` - required `path`, `alt`, and optional `name`.
- `[style]` - optional `medium`, `mood`, `palette`, and `notes`.
- `[[references]]` - optional reference image declarations.
- `[content]` - required table containing kind-specific content.

Unknown top-level fields and unknown fields inside `output`, `style`, or
`references` are rejected so typos fail fast.

## Providers

### Mock

`provider = "mock"` is the default choice for development, tests, CI, and agent
workflows. It never uses the network.

```bash
uv run visura render examples/workshop-poster.visura.toml
```

### Black Forest Labs

`provider = "bfl"` uses the BFL API and requires `BFL_API_KEY` plus `--yes`.
These examples are not locally renderable without credentials.

```bash
BFL_API_KEY=... uv run visura render examples/bfl-klein-desk-lamp.visura.toml --yes
```

BFL text-to-image sizes must be `WIDTHxHEIGHT`, use dimensions that are
multiples of 16, and stay between 64x64 and 4 megapixels. Visura currently
accepts `png` and `jpeg` output formats for BFL.

### OpenAI

OpenAI specs can be validated and compiled, but production rendering is planned
for a later milestone. Treat OpenAI examples as prompt/spec examples unless the
backend has been explicitly promoted in the current checkout.

```bash
uv run visura validate examples/my-headshot.visura.toml
uv run visura compile examples/my-headshot.visura.toml
```

### Diffusers

`provider = "diffusers"` uses Hugging Face Diffusers locally. Install the
optional dependencies first:

```bash
uv sync --extra diffusers
```

The tiny Diffusers plumbing model is useful for smoke tests:

```toml
kind = "poster"
provider = "diffusers"
model = "hf-internal-testing/tiny-stable-diffusion-pipe"
size = "64x64"
seed = 1234
output_format = "png"

[output]
path = "assets/examples/tiny-diffusers-poster.png"
alt = "Small locally rendered poster smoke test."

[content]
headline = "Local Render"
```

Run with `--yes` because a Hugging Face model ID may download weights if they
are not already cached:

```bash
uv run visura render path/to/tiny.visura.toml --yes
```

## Status And JSON

`validate`, `compile`, `render`, and `status` print JSON by default. Current
JSON is useful for inspection, but the stable agent-facing wrapper is still a
planned milestone.

```bash
uv run visura status examples/
```

`status` discovers `.visura.toml` files in directories and exits nonzero when
any asset is not clean.

## Recommended Next Build Order

1. Agent-safe CLI and batch hardening: stable response wrappers, documented exit
   codes, `--quiet`, consistent errors, complete dry-run behavior, and durable
   provider/model overrides.
2. Visura skill: a thin agent workflow that authors specs, defaults to mock,
   runs the CLI, and asks before paid/networked providers.
3. Diffusers hardening: keep the local path optional, document practical models,
   and clarify hardware/download behavior.
4. OpenAI: production rendering after mock, batch, cache, and agent guardrails
   are stable.
5. Provider reference/editing polish.

## Development

Run tests:

```bash
uv run pytest
```

Run linting and formatting:

```bash
uv run ruff check .
uv run ruff format .
```

Repository layout:

```text
src/visura/
  cli.py              Typer CLI entrypoint
  loader.py           TOML parsing and validation
  spec.py             Pydantic models for the v0 spec
  compiler.py         Spec-to-prompt payload compiler
  render.py           Cache and sidecar rendering helpers
  status.py           Asset status inspection
  backends/           Provider backends
  kinds/              Built-in kind compilers
examples/             Example .visura.toml files
tests/                Loader, CLI, backend, and e2e tests
```

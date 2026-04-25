# Visura — Product Plan

Visura is a local-first asset generation pipeline for developers.

Developers write `.visura.toml` files next to generated assets, render them locally or in CI, cache unchanged outputs, and keep sidecar metadata so every generated image is traceable. Paid image APIs are optional production backends, not required for day-to-day development.

The core promise:

> Keep generated image assets in your repo as source-controlled specs. Render cheaply with mock or local open models, use paid APIs only when final quality is worth the cost, and always know what produced each artifact.

---

## Why Developers Would Care

Typing a prompt into an image UI is fine once. It breaks down when images become part of a codebase.

Visura is useful when a project needs:

- Versioned image intent that can be reviewed in pull requests.
- Repeatable asset generation for docs, apps, marketing pages, demos, and prototypes.
- Cheap local iteration without spending money on image model APIs.
- Deterministic mock renders for tests and CI.
- Cache hits for unchanged specs.
- Sidecar metadata that records prompt, provider, model, options, references, hash, and output digest.
- A path from rough local previews to higher-quality production renders.

The project should be judged by whether a developer would rather keep image assets in Visura specs than lose them inside one-off prompts, chat threads, or ad hoc scripts.

---

## Product Shape

Visura is not just a prompt format. It is an asset workflow:

```bash
visura validate assets/**/*.visura.toml
visura compile assets/og-home.visura.toml
visura render assets/**/*.visura.toml
visura status
```

Typical spec:

```toml
kind = "poster"
provider = "mock"
model = "placeholder"
size = "1024x1536"
quality = "draft"

[output]
path = "assets/events/prompt-craft-night.png"
alt = "Poster for Prompt Craft Night workshop"

[style]
medium = "risograph event poster"
mood = "hands-on, lively, approachable"
palette = ["tomato red", "deep teal", "warm paper", "black"]

[content]
headline = "Make Images That Listen"
details = "Friday, 7 PM, Studio 12"
visual = "hands arranging paper prompt cards around a glowing monitor"
constraints = "clear headline, playful composition, no tiny body copy"
```

Backends:

- `mock`: deterministic local placeholder PNGs, always available, CI-friendly.
- `diffusers`: local Hugging Face Diffusers backend for cheap real-image iteration.
- `openai`: paid production-quality backend.

---

## Principles

- Local-first: every core workflow must work without a paid API key.
- Render early: the project becomes useful only when it produces files.
- Inspectable: `compile` should show exactly what Visura will send to a backend.
- Cache by default: unchanged specs should not regenerate or spend money.
- Provenance by default: every output should have a sidecar.
- Asset-oriented: specs should know where outputs live in a real repo.
- Provider-neutral, not provider-blind: backends can expose different capabilities, but the user should get clear validation errors.

---

## Stack

- Python 3.11+
- `pydantic` v2 for schema and validation
- `typer` for CLI
- `pillow` for mock rendering, output inspection, and reference prep
- Hugging Face `diffusers` as an optional local backend dependency
- OpenAI SDK as an optional paid backend dependency
- `uv` for dependency management
- `ruff` and `pytest` for development

---

## Revised v0 Scope

v0 should deliver the smallest complete workflow a developer can actually use:

- `visura validate`
- `visura compile`
- `visura render`
- `visura status`
- `mock` backend
- first local `diffusers` backend path
- output path support
- sidecar metadata
- content-addressed cache
- batch rendering over files/directories/globs
- one or two useful kinds

v0 should not spend time on:

- Many kinds.
- Plugin installs.
- Prompt optimization.
- LLM linting.
- Diff renderer UI.
- Full provider feature parity.
- Complex inheritance.

Those become useful after the basic asset loop is solid.

---

## Milestones

### M0 — Foundation

Current status: implemented.

Scope:

- Python package scaffold.
- CLI entrypoint.
- `validate` command.
- Pydantic spec loader.
- OpenAI backend skeleton.
- Kind/backend registries.
- Example `.visura.toml` files.
- Tests and lint configuration.

Exit criteria:

- `uv run pytest` passes.
- `uv run visura --help` works.
- `uv run visura validate examples/my-headshot.visura.toml` prints resolved JSON.

---

### M1 — Asset Spec Shape

Update the schema so specs describe assets, not only prompts.

Scope:

- Add `[output]` with `path`, `alt`, and optional `name`.
- Keep `[content]` flexible for now.
- Preserve `[style]` and `[[references]]`.
- Validate output path shape without forcing files to exist.
- Update examples to include output paths.

Exit criteria:

- Existing examples validate after migration.
- Validation catches unknown keys, bad output formats, and invalid reference declarations.
- The README shows the asset-as-code workflow.

---

### M2 — Compile

Make the model payload inspectable without rendering.

Scope:

- Add `visura compile`.
- Add a `PromptPayload` model with prompt, negative prompt when supported, options, references, and output metadata.
- Implement the first kind compiler, likely `poster` or `product_mockup`.
- Add shared style/content helpers for prompt fragments.
- Print JSON by default; optionally support a human-readable format later.

Exit criteria:

- `visura compile examples/workshop-poster.visura.toml` prints the compiled prompt and backend options.
- No API calls are made by compile.
- Tests cover successful compile, unknown kind, and invalid kind-specific content.

---

### M3 — Mock Render Backend

Make rendering work with zero external services.

Scope:

- Add `provider = "mock"`.
- Implement deterministic Pillow PNG generation.
- Placeholder image should include useful debug information: kind, output path, size, prompt hash, provider, model, and a short prompt excerpt.
- Support requested size and output format where practical.
- Add `visura render`.

Exit criteria:

- `visura render examples/workshop-poster.visura.toml` writes a PNG without network access.
- Output is deterministic for the same resolved spec.
- Tests can render through `mock` in CI.

---

### M4 — Cache And Sidecars

Make the workflow affordable and traceable.

Scope:

- Compute a canonical render hash from resolved spec, compiled prompt, references, provider, model, seed, compiler version, and backend version.
- Store rendered artifacts in a content-addressed cache.
- Restore outputs from cache when possible.
- Write sidecars next to outputs.
- Add `--force` to bypass cache.

Sidecar should include:

- Spec snapshot.
- Compiled prompt.
- Provider and model.
- Backend options.
- Render hash.
- Reference file digests.
- Output path.
- Output digest.
- Timestamp.
- Cache hit/miss.

Exit criteria:

- Rendering the same spec twice uses one generation and one cache hit.
- Deleting an output and rerendering restores from cache.
- Sidecar metadata is enough to understand what happened without reading logs.

---

### M5 — Batch And Status

Make Visura useful in real repos with many assets.

Scope:

- Accept files, directories, and globs.
- Add `visura status`.
- Report missing outputs, stale outputs, cache hits available, and specs that validate.
- Make command output concise enough for CI logs.

Exit criteria:

- `visura render assets/` renders every spec under the directory.
- `visura status assets/` identifies stale or missing artifacts.
- CI can run `visura status --check` and fail when generated assets are out of date.

---

### M6 — Local Diffusers Backend

Add a real local image backend for cheap iteration.

Scope:

- Add optional Diffusers dependencies.
- Support a tiny test model for plumbing, such as `hf-internal-testing/tiny-stable-diffusion-pipe`.
- Document `stabilityai/sdxl-turbo` as the practical local draft-quality model.
- Normalize common options: size, seed, steps, guidance scale, device, dtype.
- Cache loaded pipelines within a process.

Exit criteria:

- A developer can render locally without an API key.
- Tiny Diffusers pipeline can be exercised in tests or marked integration tests.
- SDXL Turbo docs include a known-good command for machines with compatible hardware.

---

### M7 — Paid Backend Polish

Make OpenAI useful after the local loop already works.

Scope:

- Implement OpenAI rendering behind the same render interface.
- Validate unsupported options clearly.
- Support references where the backend supports them.
- Record request metadata in the sidecar.
- Ensure cache prevents accidental repeat paid calls.

Exit criteria:

- Switching a spec from `provider = "mock"` or `provider = "diffusers"` to `provider = "openai"` requires minimal changes.
- Paid renders always write sidecars.
- Re-running unchanged paid specs hits cache by default.

---

### M8 — Docs And Distribution

Make the project understandable to a stranger.

Scope:

- README quickstart with mock render first.
- Local Diffusers guide.
- Paid backend guide.
- Asset workflow examples for docs images, product mockups, posters, OG images, and demo data.
- License.
- Publish package when the v0 loop is stable.

Exit criteria:

- A stranger can clone the repo and render a mock image in under one minute.
- A stranger with local model hardware can render through Diffusers without an API key.
- The README clearly explains when Visura is better than a prompt pasted into an image UI.

---

## Deferred

| Version | Features |
|---|---|
| v0.5 | `extends`, watch mode, visual diff summaries, reference image polish |
| v1 | Prompt linter, eval suite, post-render critic loop |
| v1.5 | Prompt optimization, few-shot cache, authoring assistant |
| v2 | External backend plugins, kind plugin installs, web UI |

---

## Success Criteria

- A developer can use Visura without any paid API key.
- `mock` backend is fast and deterministic enough for CI.
- Local Diffusers renders are documented and usable.
- Rendering unchanged specs is a cache hit.
- Sidecars make generated assets auditable.
- Specs live naturally beside real repo assets.
- The README pitch is about asset generation workflows, not just TOML prompts.

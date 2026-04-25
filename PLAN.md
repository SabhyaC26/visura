# Visura — Product Plan

Visura is a local-first asset generation pipeline for developers and coding agents.

Developers and agents write `.visura.toml` files next to generated assets, render them locally or in CI, cache unchanged outputs, and keep sidecar metadata so every generated image is traceable. Paid image APIs are optional production backends, not required for day-to-day development.

The core promise:

> Keep generated image assets in your repo as source-controlled specs. Render cheaply with mock or local open models, use paid APIs only when final quality is worth the cost, and always know what produced each artifact.

The CLI and TOML spec are the stable engine. A Visura skill should sit on top as the agent-native UX layer: it teaches coding agents how to author specs, run the CLI safely, inspect JSON output, and avoid paid backends unless explicitly requested.

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
- A CLI that coding agents can call safely while editing a repo.

The project should be judged by whether a developer or coding agent would rather keep image assets in Visura specs than lose them inside one-off prompts, chat threads, or ad hoc scripts.

---

## Product Shape

Visura is not just a prompt format. It is an asset workflow:

```bash
visura validate assets/**/*.visura.toml
visura compile assets/og-home.visura.toml
visura render assets/**/*.visura.toml
visura status
```

The human-friendly CLI and agent-friendly CLI should be the same commands with different output modes:

```bash
visura status assets/ --json
visura compile assets/og-home.visura.toml --json
visura render assets/ --json --yes
visura render assets/ --dry-run --json
```

Coding agents should be able to use Visura without scraping prose logs, guessing output paths, or accidentally triggering paid API calls.

The optional Visura skill should not replace the CLI. It should wrap it:

- Author or edit `.visura.toml` specs from natural language requests.
- Default to `provider = "mock"` for development.
- Run `visura validate --json`, `visura compile --json`, `visura render --json`, and `visura status --json`.
- Interpret JSON results for the user.
- Ask before switching to paid backends.
- Leave durable specs, outputs, sidecars, and cache entries in the repo.

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
- Agent-friendly: every command should have stable machine-readable output and predictable side effects.
- Skill-compatible: a Visura skill should improve agent UX while delegating durable work to the CLI.
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
- JSON output modes for agent callers
- optional Visura skill workflow
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

## Agent-Friendly CLI Contract

Coding agents such as Codex, Claude Code, and other repo-editing tools are first-class users. They need commands that are deterministic, inspectable, and easy to recover from.

Every command should support:

- `--json` for stable machine-readable output.
- `--quiet` for minimal logs.
- Clear exit codes.
- No progress spinners or interactive prompts when stdout is not a TTY.
- Absolute or repo-relative file paths in JSON output.
- Structured errors with code, message, path, and field location when available.

Commands that can spend money or overwrite files should support:

- `--dry-run` to report planned actions.
- `--yes` or `--no-confirm` to make intentional non-interactive execution explicit.
- `--max-cost` once paid backends can estimate cost.
- `--provider` and `--model` overrides so agents can force `mock` or local providers during development.
- Cache-first defaults so reruns are safe.

JSON output should be stable enough for agents to parse across patch releases. Human-readable text can improve over time; JSON shape should be versioned.

Example render result:

```json
{
  "schema_version": "0.1",
  "command": "render",
  "ok": true,
  "results": [
    {
      "spec_path": "assets/og-home.visura.toml",
      "output_path": "assets/og-home.png",
      "sidecar_path": "assets/og-home.visura.json",
      "provider": "mock",
      "model": "placeholder",
      "cache": "hit",
      "render_hash": "sha256:..."
    }
  ]
}
```

## Skill Layer

Visura should ship or document an optional skill for agent environments, but the skill should be a thin workflow layer rather than the source of truth.

The skill is responsible for:

- Translating a user's request into a good `.visura.toml` spec.
- Choosing a reasonable `kind`, `size`, `output.path`, `style`, and `content` shape.
- Running safe CLI commands in the right order.
- Reading JSON output and explaining only the relevant result.
- Using `mock` or local backends by default.
- Asking before paid renders or destructive overwrites.
- Updating README/docs references when generated assets are meant to be used by the project.

The skill is not responsible for:

- Owning the spec schema.
- Hiding generated asset state in an agent transcript.
- Replacing cache, sidecars, or status checks.
- Creating a workflow that only works in one agent product.

The product boundary should stay clear:

- CLI/TOML/cache/sidecar: durable repo-native engine.
- Skill: agent-native authoring and orchestration layer.

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

### M6 — Agent-Friendly CLI

Make Visura easy and safe for coding agents to operate.

Scope:

- Add `--json` to `validate`, `compile`, `render`, and `status`.
- Define a versioned JSON response schema.
- Add structured error objects with stable error codes.
- Add `--dry-run` for commands with file or cost side effects.
- Add explicit non-interactive flags for commands that overwrite files or may spend money.
- Add provider/model overrides so agents can force `mock` during development.
- Document exit codes and command contracts.
- Ensure logs and progress output go to stderr when JSON is written to stdout.

Exit criteria:

- An agent can run `visura status --json` and decide which specs need rendering.
- An agent can run `visura render --dry-run --json` and report planned file changes without writing outputs.
- An agent can force `provider = "mock"` from the CLI to avoid paid calls.
- JSON output includes all file paths and cache decisions needed for follow-up edits.
- Tests cover JSON success and error responses.

---

### M7 — Visura Skill

Make the agent workflow easy without making it agent-only.

Scope:

- Draft a Visura skill that teaches agents the recommended workflow.
- Default the skill to mock renders and JSON CLI calls.
- Include guidance for authoring useful specs from natural language.
- Include guardrails for paid providers and overwrites.
- Document how the skill should handle `validate`, `compile`, `render`, and `status`.
- Keep the skill thin: it should call Visura rather than reimplementing Visura behavior.

Exit criteria:

- An agent can turn "make an OG image for this page" into a checked-in `.visura.toml` plus mock output.
- The skill uses `visura status --json` and `visura render --json` instead of parsing human logs.
- The skill asks before paid provider usage.
- The same repo workflow still works without the skill.

---

### M8 — Local Diffusers Backend

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

### M9 — Paid Backend Polish

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

### M10 — Docs And Distribution

Make the project understandable to a stranger.

Scope:

- README quickstart with mock render first.
- Agent/skill workflow guide.
- Local Diffusers guide.
- Paid backend guide.
- Asset workflow examples for docs images, product mockups, posters, OG images, and demo data.
- License.
- Publish package when the v0 loop is stable.

Exit criteria:

- A stranger can clone the repo and render a mock image in under one minute.
- An agent can follow the documented skill workflow without special project knowledge.
- A stranger with local model hardware can render through Diffusers without an API key.
- The README clearly explains when Visura is better than a prompt pasted into an image UI.

---

## Deferred

| Version | Features |
|---|---|
| v0.5 | `extends`, watch mode, visual diff summaries, reference image polish |
| v1 | Prompt linter, eval suite, post-render critic loop |
| v1.5 | Prompt optimization, few-shot cache, authoring assistant |
| v2 | External backend plugins, kind plugin installs, web UI, MCP server |

---

## Success Criteria

- A developer can use Visura without any paid API key.
- Coding agents can use Visura through stable JSON output and non-interactive flags.
- A Visura skill can orchestrate the CLI without becoming the source of truth.
- `mock` backend is fast and deterministic enough for CI.
- Local Diffusers renders are documented and usable.
- Rendering unchanged specs is a cache hit.
- Sidecars make generated assets auditable.
- Specs live naturally beside real repo assets.
- The README pitch is about asset generation workflows, not just TOML prompts.

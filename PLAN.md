# Visura Product Plan

Visura is a local-first asset generation pipeline for developers and coding
agents. Specs live in the repo, renders are reproducible, unchanged artifacts
come from cache, and sidecars explain what produced each generated image.

The product should stay useful without paid API keys. Paid or networked
providers are production backends, not the default development loop.

## Current State

Implemented:

- Spec loading and validation for `.visura.toml`.
- `validate`, `compile`, `render`, and `status` commands.
- Deterministic local `mock` rendering.
- Content-addressed cache under `.visura/cache`.
- Render sidecars with spec, prompt payload, provider/model, hash, output
  digest, references, timestamp, and cache decision.
- Status inspection for clean, missing, stale, changed, and invalid assets.
- BFL rendering path gated by API key and `--yes`.
- First optional Diffusers rendering path for local model execution.
- Example specs for common asset types.
- Versioned CLI response wrappers with `schema_version`, `command`, `ok`,
  `results`, and structured `errors`.
- `--quiet` for suppressing human-readable stderr summaries.
- Batch render/status behavior for files, directories, and globs.

Partially implemented:

- `render` has `--dry-run`, `--force`, `--yes`, `--provider`, and `--model`;
  provider/model overrides also exist for `compile`.
- Provider/model override semantics are in place for compile/render, but future
  provider-specific capabilities still need more documentation.

Not implemented:

- A packaged Visura skill.
- Production OpenAI rendering.

## Product Shape

The durable engine is the CLI, TOML schema, cache, and sidecars:

```bash
visura validate assets/og-home.visura.toml
visura compile assets/og-home.visura.toml
visura render assets/og-home.visura.toml --provider mock --model placeholder
visura status assets/
```

The agent workflow should be the same engine with stricter output contracts:

```bash
visura status assets/ --json
visura render assets/ --dry-run --json
visura render assets/ --provider mock --model placeholder --json
```

Agents should never need to scrape prose logs, guess output paths, or risk a
paid render unless the user explicitly approves it.

## Backend Status

| Provider | Current state | Intended role |
|---|---|---|
| `mock` | Implemented | Default local, CI, and agent-safe render backend |
| `bfl` | Rendering path exists | Networked paid/high-quality backend behind key + `--yes` |
| `openai` | Scaffold-only for the current milestone | Future paid production backend |
| `diffusers` | First optional path exists | Local real-image iteration backend, still needs hardening and docs |

## CLI Contract

The current agent-facing CLI contract is:

- Versioned response wrappers with `schema_version`, `command`, `ok`, and
  `results`.
- Stable structured errors with code, message, path, and field location when
  available.
- `--quiet` for minimal logs.
- Consistent dry-run behavior for commands with write or cost side effects.
- Provider/model override semantics for safe local rendering.
- Documented exit codes.
- Logs and progress on stderr whenever JSON is on stdout.

## Recommended Next Build Order

1. **Visura skill**

   Add a thin skill that turns natural language into specs, defaults to
   `provider = "mock"`, runs `validate`, `compile`, `render`, and `status`, and
   asks before paid or networked providers. The skill should not own schema or
   rendering logic.

2. **Diffusers hardening**

   Keep the new local rendering path optional, verify the tiny plumbing model,
   document a practical draft model, and clarify hardware/download behavior.

3. **OpenAI backend**

   Promote OpenAI from scaffold to production rendering after local and
   agent-safe workflows are stable. Paid renders must be cache-first,
   sidecar-backed, and require explicit approval.

4. **Provider polish**

   Add reference/image-editing support, provider-specific capability docs, and
   distribution polish.

## Milestone Map

Completed milestones:

- M0 Foundation: package, CLI entrypoint, spec loader, validation, examples, and
  tests.
- M1 Asset spec shape: `[output]`, flexible `[content]`, `[style]`, and
  references.
- M2 Compile: prompt payload generation without rendering.
- M3 Mock render: deterministic local images.
- M4 Cache and sidecars: traceable, cache-first rendering.
- M5 Status baseline: inspect outputs, sidecars, cache, and spec drift.
- M6 BFL path: first networked provider render path.
- M7 Diffusers baseline: first optional local model render path.
- M8 Agent-safe CLI and batch contract.

Next milestones:

- M9 Visura skill.
- M10 Diffusers hardening and docs.
- M11 OpenAI production backend.
- M12 Reference/edit workflows and distribution.

## Success Criteria

- A developer can clone the repo and render a mock image in under one minute.
- Coding agents can operate Visura through stable JSON and predictable side
  effects.
- Unchanged renders hit cache by default.
- Sidecars make generated assets auditable without reading logs.
- Paid or networked renders require explicit approval.
- Diffusers stays optional and local-first; OpenAI arrives after the
  local/agent-safe loop is solid.

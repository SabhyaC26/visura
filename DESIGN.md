# Visura Design

Visura treats generated images as repo-native assets. The source of truth is a
`.visura.toml` spec; rendered files are derived artifacts with cache entries and
sidecars.

## Goals

- Local-first asset generation with `mock` as the default development backend.
- Specs that can be validated, compiled, reviewed, and committed.
- Renders that are cacheable and traceable.
- A CLI contract that coding agents can use without scraping logs.
- Paid or networked providers behind explicit approval.

## Pipeline

```text
.visura.toml
  -> load and validate
  -> compile prompt payload
  -> render with provider
  -> write output image
  -> write sidecar metadata
  -> store or restore from .visura/cache
  -> inspect with status
```

`compile` never renders or calls a provider. `render` owns cache/sidecar writes.
`status` recomputes the current render hash and compares it with the output,
sidecar, and cache state.

## Current Components

- `loader.py` parses TOML and validates the spec model.
- `compiler.py` turns flexible content into provider-ready prompt payloads.
- `backends/mock.py` renders deterministic local placeholders.
- `backends/bfl.py` contains the networked BFL rendering path.
- `backends/diffusers.py` contains the optional local Diffusers rendering path.
- `render.py` computes render hashes, restores/writes cache entries, and writes
  sidecars.
- `status.py` discovers specs and reports asset state.
- `cli.py` exposes `validate`, `compile`, `render`, and `status`.

## Backend Design

| Provider | Design status | Notes |
|---|---|---|
| `mock` | Implemented | Local, deterministic, no network, suitable for CI |
| `bfl` | Implemented path | Requires `BFL_API_KEY` and `--yes` |
| `openai` | Scaffold-only in current docs | Planned paid production backend |
| `diffusers` | First optional path exists | Local model execution, still needs hardening and docs |

Provider differences should be explicit capability checks, not hidden behavior.
Unsupported options should fail before spending money or writing files.

## CLI Design

Current CLI output is JSON by default. That is useful, but agent compatibility
needs a stable contract:

```json
{
  "schema_version": "0.1",
  "command": "render",
  "ok": true,
  "results": []
}
```

The current implementation should be treated as provisional until this wrapper,
structured errors, `--quiet`, exit-code docs, and batch guarantees are complete.

Commands with side effects should support dry-run planning. Commands that may
spend money or use the network should require explicit approval such as `--yes`.
Provider/model overrides let agents force `mock` without rewriting a spec.

## Sidecar And Cache

Every render should leave enough metadata to audit the artifact:

- resolved spec snapshot
- compiled prompt payload
- provider and model
- render hash
- reference digests
- output path and digest
- cache decision
- timestamp

Cache keys are content-addressed from the resolved spec, compiled payload,
backend identity, compiler version, Visura version, and reference digests.

## Recommended Next Build Order

1. Agent-safe CLI and batch contract.
2. Thin Visura skill for coding agents.
3. Diffusers hardening and documentation.
4. Production OpenAI backend.
5. Provider reference/edit workflows.

This order keeps the local, auditable loop stable before adding more expensive
or environment-sensitive rendering paths.

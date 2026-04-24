# Visura — v0 Plan

A Python library for declarative, replayable image generation on top of image models. Users author `.visura.toml` files; the library validates, compiles to a model-aware render payload, renders through a backend adapter, and writes a sidecar so every output is traceable, cacheable, and reproducible from Visura's own artifact cache.

---

## Scope

### v0 is

- Write a `.visura.toml`, run `visura render foo.visura.toml`, get an image.
- Two kinds shipped (one to prove the pattern, one to prove it generalizes).
- A model/provider abstraction from day one, with one production-quality bundled backend to keep v0 shippable.
- Replayable outputs: sidecar metadata + deterministic content-addressable cache from day one.
- Readable enough that the author reaches for it over typing a prose prompt in ChatGPT.

### v0 is NOT

- Inheritance / `extends` — v0.5.
- Eval suite, optimizer, few-shot cache — v1.
- LLM-powered linter, authoring assistant, reverse compiler — v1.
- Full provider feature parity — v1+. v0 proves the abstraction without pretending every image API has the same knobs.
- Diff renderer — v0.5. The killer feature lands *after* there are real specs to diff.

The cut list is the point. Each parked item is a multi-week rabbit hole; v0 ships without any of them.

---

## Stack

- Python 3.11+ (stdlib `tomllib`, modern typing)
- `pydantic` v2 — schema + validation
- Provider SDKs behind small backend adapters — start with OpenAI, keep the core provider-neutral
- `typer` — CLI
- `pillow` — reference image prep (resize, encode)
- `uv` — dependency management
- `ruff` — lint + format
- `pytest` — tests

---

## Repo layout

```
visura/
├── pyproject.toml
├── README.md
├── .env.example                     # provider API key examples
├── src/visura/
│   ├── __init__.py
│   ├── cli.py                       # typer entrypoint
│   ├── spec.py                      # pydantic: Envelope, Style, References
│   ├── loader.py                    # parse + validate .visura.toml → Spec
│   ├── kinds/
│   │   ├── __init__.py              # registry + dispatch
│   │   ├── base.py                  # Kind protocol, shared fragments
│   │   └── headshot.py              # first kind
│   ├── backends/
│   │   ├── __init__.py              # backend registry + resolver
│   │   ├── base.py                  # Backend protocol + capabilities
│   │   └── openai.py                # first bundled backend
│   ├── render.py                    # backend dispatch + reference pipeline
│   ├── cache.py                     # content-addressable cache
│   ├── sidecar.py                   # write .visura.meta.json
│   └── hashing.py                   # canonical hash of spec + refs + seed
├── examples/
│   ├── my-headshot.visura.toml
│   └── blueprint.visura.toml
└── tests/
    ├── test_loader.py
    ├── test_compiler_headshot.py
    ├── test_cache.py
    └── fixtures/
        ├── headshot-minimal.visura.toml
        └── ref-selfie.jpg
```

---

## Milestones

### M0 — Foundation

Get the boring stuff right once so it never blocks real work later.

**Scope**
- Project scaffold via `uv init`.
- `pyproject.toml` with deps, CLI entrypoint, package metadata.
- `ruff` config, `pytest` config.
- GitHub Actions CI: lint + test on push.
- `.env.example`, `.gitignore`.

**Exit criteria**
- `uv sync && uv run pytest` runs (one no-op test passing).
- `uv run visura --help` prints help text.
- CI green on an empty PR.

---

### M1 — Spec + loader

The `.visura.toml` format exists and round-trips cleanly through the library. The desired authoring surface drives the schema, but the first schema should settle the important shape: `[content]`, `[style]`, optional `[[references]]`, and an envelope with model/provider controls.

**Scope**
- `spec.py`: pydantic models for `Envelope` (provider, model, seed, size, kind, quality, output_format, background), `Style`, `References`. `content` stays as `dict[str, Any]` at envelope level — kind-specific schemas validate it in M2.
- `loader.py`: `tomllib` parse → pydantic validate → typed `Spec` object. Clear errors on malformed input.
- `kinds/__init__.py`: registry with a `@register("headshot")` decorator. Zero kinds registered at M1 exit — the infrastructure exists, implementations come in M2.
- `backends/__init__.py`: registry with a bundled OpenAI backend configured as the default, while preserving `provider` as a real spec field.
- `cli.py`: `visura validate foo.visura.toml` — parses, validates, pretty-prints the resolved spec. No rendering yet.
- One `examples/my-headshot.visura.toml` hand-written before the schema is finalized (let the desired authoring surface drive the schema).

**Exit criteria**
- `visura validate examples/my-headshot.visura.toml` succeeds.
- `visura validate` on a malformed TOML surfaces a pinpoint error.
- Tests cover: happy path, missing required field, wrong type, unknown top-level key.

---

### M2 — First compiler + render pipeline

End-to-end: TOML in, compiled prompt inspectable, PNG out.

**Scope**
- `kinds/headshot.py`: kind-specific content schema (`subject`, `pose`, `expression`, `background`, `lighting`) + a compiler function `(envelope, content) -> PromptPayload`. Where `PromptPayload` carries the prompt string, any reference image bytes, and role tags.
- `kinds/base.py`: shared helpers for style/palette/medium fragments that every kind reuses.
- `backends/base.py`: `ImageBackend` protocol with declared capabilities (references, seed support, output formats, supported sizes, provider-specific options).
- `backends/openai.py`: first bundled implementation. It owns OpenAI API shape churn, including whether a render uses generation, edit, or Responses-style image calls.
- `render.py`: provider-neutral dispatcher. It resolves a backend, asks it to normalize/validate render options, and handles shared reference image prep where possible.
- `cache.py` + `sidecar.py`: minimal first pass wired into render immediately, so paid API calls always leave provenance and repeat runs can hit the artifact cache.
- `cli.py`: `visura render foo.visura.toml` produces a PNG in the current directory.
- `cli.py`: `visura compile foo.visura.toml` prints the compiled prompt and resolved render payload without making an API call.

**Exit criteria**
- Rendering a real headshot TOML produces an image the author would actually use.
- Compiling the same TOML prints an inspectable prompt without touching the API.
- Informal A/B: the compiled prompt produces comparable-or-better results than the equivalent prose prompt the author would have written by hand.
- Reference image pipeline handles both "no references" and "one likeness reference" paths.
- First render writes a sidecar with spec snapshot, compiled prompt, render hash, provider, model name, seed, timestamp, and output path.
- The OpenAI backend is swappable in code without changing kind compilers.

---

### M3 — Cache + replayability layer

Deletable outputs. Cacheable re-runs. Honest provenance. Visura guarantees byte-identical artifacts from its own cache; fresh remote regenerations are replay attempts unless the selected backend explicitly guarantees deterministic image bytes for the pinned model and seed.

**Scope**
- `hashing.py`: canonical hash of `(resolved spec + reference image bytes + provider + model name/snapshot when available + seed + compiler version + backend version)`. TOML key ordering must not affect hash.
- `cache.py`: harden the content-addressable cache keyed on that hash. `--force` flag overrides.
- `sidecar.py`: expand `foo.visura.meta.json` next to each output PNG with backend request snapshot, final compiled prompt, provider, model name/snapshot when available, seed, hash, timestamp, output file digest, and API cost estimate when available.
- Render command can restore a deleted PNG from cache without making an API call.

**Exit criteria**
- Running the same TOML twice is one API call. Second run logs "cache hit".
- Deleting the PNG and re-rendering restores an identical cached artifact when the cache entry exists.
- `--force` bypasses cache, makes a fresh API call, and records the new artifact digest in the sidecar.
- Opening the sidecar reveals everything needed to understand what was generated and why.

---

### M4 — CLI polish

The surface a stranger would encounter.

**Scope**
- Flags: `--output-dir`, `--force`, `--seed` (override), and `render --dry-run` as an alias for `compile`.
- `visura validate` and `visura render` both surface useful errors — no raw pydantic tracebacks reaching the user.
- `visura --version` returns the package version.
- Exit codes: 0 success, 1 validation error, 2 API error, 3 cache/IO error.

**Exit criteria**
- A stranger can clone the repo, add an API key, run the example TOML, and succeed without asking questions.
- Error messages for the top 5 likely mistakes (missing key, wrong kind, unreadable reference image, unsupported model option, provider auth failure) are readable.

---

### M5 — Second kind

Prove the abstraction generalizes. Prefer the second kind that produces three genuinely useful examples fastest. `blueprint` or `infographic` are high-upside because they stress labels, layout, and in-image text; `product_mockup`, `poster`, or `album_cover` are lower-risk if the abstraction itself is the thing being tested.

**Scope**
- New kind module under `kinds/`.
- Kind-specific content schema.
- Compiler that reuses `kinds/base.py` fragments but adds kind-specific instructions.
- Example TOML under `examples/`.

**Exit criteria**
- Two kinds coexist with zero cross-contamination in code.
- Both produce output the author is happy with.
- Adding a third kind (hypothetically) requires no changes outside `kinds/`.

---

### M6 — Docs + publish

Make it possible for one more person to use it.

**Scope**
- README: install, quickstart, one before/after (prose prompt vs. TOML) per kind, cache/replayability demo, deferred-features list.
- Docstrings on public API surface (`render`, `validate`, `Spec`).
- Publish to PyPI as `visura`.
- License (MIT or Apache 2.0).

**Exit criteria**
- `pip install visura && visura render foo.visura.toml` works for a stranger.
- The README answers: what is this, why does it exist, how do I try it in 60 seconds, what's *not* here yet.

---

## Success criteria for v0

- [ ] 5+ TOMLs in `examples/` that the author actually wants to keep.
- [ ] Re-running any example is a cache hit (zero API cost).
- [ ] Sidecar metadata is sufficient to understand and replay the render; the cache is sufficient to restore the exact image bytes.
- [ ] Any TOML is < 20 lines for a non-trivial image, and more readable than the prose equivalent.
- [ ] Informally: the compiled prompt produces comparable-or-better results than the prose prompt the author would have written.
- [ ] Two kinds shipped, both dogfooded.

---

## Deferred list (pin this)

| Version | Features |
|---|---|
| v0.5 | `extends`/inheritance, watch mode, diff renderer, 3rd–5th kinds |
| v1 | Eval suite (promptfoo-style), post-render critic loop, semantic linter |
| v1.5 | Few-shot bootstrap cache, optimizer (GEPA-style), authoring assistant |
| v2 | External backend plugins, kind plugin installs, web UI |

---

## First three files to write (literal order)

1. `examples/my-headshot.visura.toml` — write the TOML you *wish* existed. Let the desired authoring surface drive the schema, not the other way around.
2. `src/visura/spec.py` — pydantic models that validate the example you just wrote, including the minimal provider/model render controls.
3. `src/visura/kinds/headshot.py` — the compiler. Start ugly, get it end-to-end, then tighten.

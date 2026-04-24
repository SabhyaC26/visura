# Visura — v0 Plan

A Python library for declarative, reproducible image generation on top of gpt-image-2. Users author `.visura.toml` files; the library validates, compiles to a tuned prompt, renders via the OpenAI API, and writes a sidecar so every output is reproducible.

---

## Scope

### v0 is

- Write a `.visura.toml`, run `visura render foo.visura.toml`, get an image.
- Two kinds shipped (one to prove the pattern, one to prove it generalizes).
- One model backend (gpt-image-2).
- Reproducible outputs: sidecar metadata + deterministic content-addressable cache from day one.
- Readable enough that the author reaches for it over typing a prose prompt in ChatGPT.

### v0 is NOT

- Inheritance / `extends` — v0.5.
- Eval suite, optimizer, few-shot cache — v1.
- LLM-powered linter, authoring assistant, reverse compiler — v1.
- Multi-model backend — parked until v0 proves itself on one.
- Diff renderer — v0.5. The killer feature lands *after* there are real specs to diff.

The cut list is the point. Each parked item is a multi-week rabbit hole; v0 ships without any of them.

---

## Stack

- Python 3.11+ (stdlib `tomllib`, modern typing)
- `pydantic` v2 — schema + validation
- `openai` — gpt-image-2 client
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
├── .env.example                     # OPENAI_API_KEY
├── src/visura/
│   ├── __init__.py
│   ├── cli.py                       # typer entrypoint
│   ├── spec.py                      # pydantic: Envelope, Style, References
│   ├── loader.py                    # parse + validate .visura.toml → Spec
│   ├── kinds/
│   │   ├── __init__.py              # registry + dispatch
│   │   ├── base.py                  # Kind protocol, shared fragments
│   │   └── headshot.py              # first kind
│   ├── render.py                    # gpt-image-2 call, reference pipeline
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

The `.visura.toml` format exists and round-trips cleanly through the library.

**Scope**
- `spec.py`: pydantic models for `Envelope` (model, seed, size, kind), `Style`, `References`. `content` stays as `dict[str, Any]` at envelope level — kind-specific schemas validate it in M2.
- `loader.py`: `tomllib` parse → pydantic validate → typed `Spec` object. Clear errors on malformed input.
- `kinds/__init__.py`: registry with a `@register("headshot")` decorator. Zero kinds registered at M1 exit — the infrastructure exists, implementations come in M2.
- `cli.py`: `visura validate foo.visura.toml` — parses, validates, pretty-prints the resolved spec. No rendering yet.
- One `examples/my-headshot.visura.toml` hand-written before the schema is finalized (let the desired authoring surface drive the schema).

**Exit criteria**
- `visura validate examples/my-headshot.visura.toml` succeeds.
- `visura validate` on a malformed TOML surfaces a pinpoint error.
- Tests cover: happy path, missing required field, wrong type, unknown top-level key.

---

### M2 — First compiler + render pipeline

End-to-end: TOML in, PNG out.

**Scope**
- `kinds/headshot.py`: kind-specific content schema (`subject`, `pose`, `expression`, `background`, `lighting`) + a compiler function `(envelope, content) -> PromptPayload`. Where `PromptPayload` carries the prompt string, any reference image bytes, and role tags.
- `kinds/base.py`: shared helpers for style/palette/medium fragments that every kind reuses.
- `render.py`: thin wrapper around the OpenAI client. Dispatches to `/v1/images/generations` when no references are present, `/v1/images/edits` when they are. Handles reference image prep: load, resize to supported dims, base64, attach with role context.
- `cli.py`: `visura render foo.visura.toml` produces a PNG in the current directory.

**Exit criteria**
- Rendering a real headshot TOML produces an image the author would actually use.
- Informal A/B: the compiled prompt produces comparable-or-better results than the equivalent prose prompt the author would have written by hand.
- Reference image pipeline handles both "no references" and "one likeness reference" paths.

---

### M3 — Reproducibility layer

Deletable outputs. Cacheable re-runs. Traceable provenance.

**Scope**
- `hashing.py`: canonical hash of `(resolved spec + reference image bytes + model snapshot + seed + compiler version)`. TOML key ordering must not affect hash.
- `cache.py`: content-addressable cache keyed on that hash. `--force` flag overrides.
- `sidecar.py`: write `foo.visura.meta.json` next to each output PNG containing spec snapshot, final compiled prompt, model snapshot, seed, hash, timestamp, API cost estimate.
- Wire caching + sidecar into the render command.

**Exit criteria**
- Running the same TOML twice is one API call. Second run logs "cache hit".
- Deleting the PNG and re-rendering produces an identical file (same hash).
- Opening the sidecar reveals everything needed to understand what was generated and why.

---

### M4 — CLI polish

The surface a stranger would encounter.

**Scope**
- Flags: `--output-dir`, `--force`, `--dry-run` (prints compiled prompt, skips API call), `--seed` (override).
- `visura validate` and `visura render` both surface useful errors — no raw pydantic tracebacks reaching the user.
- `visura --version` returns the package version.
- Exit codes: 0 success, 1 validation error, 2 API error, 3 cache/IO error.

**Exit criteria**
- A stranger can clone the repo, add an API key, run the example TOML, and succeed without asking questions.
- Error messages for the top 5 likely mistakes (missing key, wrong kind, unreadable reference image, invalid seed, API auth failure) are readable.

---

### M5 — Second kind

Prove the abstraction generalizes. Ship either `blueprint` or `infographic` — both showcase gpt-image-2 strengths that prose prompts genuinely struggle with (labels, layout, in-image text). Decide based on which the author most wants to use.

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
- README: install, quickstart, one before/after (prose prompt vs. TOML) per kind, reproducibility demo, deferred-features list.
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
- [ ] Sidecar metadata is sufficient that deleting the PNG and re-running reproduces the exact image.
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
| v2 | Multi-model backend, kind plugin installs, web UI |

---

## First three files to write (literal order)

1. `examples/my-headshot.visura.toml` — write the TOML you *wish* existed. Let the desired authoring surface drive the schema, not the other way around.
2. `src/visura/spec.py` — pydantic models that validate the example you just wrote.
3. `src/visura/kinds/headshot.py` — the compiler. Start ugly, get it end-to-end, then tighten.

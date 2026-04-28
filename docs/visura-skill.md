# Visura Agent Workflow

This is a thin workflow layer for coding agents. The Visura CLI, TOML schema,
cache, and sidecars are the source of truth. Do not redefine the product or
invent schema fields; inspect existing examples and CLI help when a checkout
differs from this document.

## Default Stance

- Convert natural language image requests into a `.visura.toml` file near the
  intended asset, using existing repo asset paths and naming conventions.
- Default development specs to `provider = "mock"` and `model = "placeholder"`.
- Choose the closest supported `kind`. For OG images, social images, banners,
  or title cards, use `kind = "poster"` unless the repo has a more specific
  supported kind.
- Keep `[content]` concrete: include the headline or subject the compiler
  requires, plus short fields for the scene, visual elements, constraints, and
  any text that must be readable.
- Always include an `[output]` table with a repo-relative `path` and useful
  `alt` text.
- Update app code, metadata, README references, or docs links only when the
  request or a follow-up makes it clear that the rendered asset is intended to
  be used by the project, and those files are in scope.

## Safe Command Order

Run commands from the repo root.

1. Validate the spec:

   ```bash
   uv run visura validate path/to/asset.visura.toml
   ```

   Expect resolved spec JSON on stdout. Fix TOML, schema, or missing-field
   errors before continuing.

2. Compile the prompt payload:

   ```bash
   uv run visura compile path/to/asset.visura.toml
   ```

   Expect JSON with `prompt`, `options`, `references`, and `output`. Review it
   before rendering, especially text, size, provider, model, and output path.

3. Inspect current asset state:

   ```bash
   uv run visura status path/to/asset.visura.toml
   ```

   Expect a JSON array. Report only the useful state to the user: `clean`,
   `missing_output`, `missing_sidecar`, `stale`, `changed`, or `invalid`.

4. Prefer a dry run before writes or paid work when the CLI supports it:

   ```bash
   uv run visura render path/to/asset.visura.toml --dry-run --json
   ```

   In the current v0 CLI, `validate`, `compile`, `render`, and `status` already
   print JSON by default, and `render` does not expose `--dry-run` or `--json`.
   Check `uv run visura render --help` before passing optional flags.

5. Render only after validation, compile review, and status inspection:

   ```bash
   uv run visura render path/to/asset.visura.toml
   ```

6. Re-run status after rendering:

   ```bash
   uv run visura status path/to/asset.visura.toml
   ```

## Paid And Network Providers

- Ask the user before using a paid or networked provider such as `openai` or
  `bfl`, before adding `--yes`, or before relying on API keys.
- If provider/model override flags are available in the checkout, use them for
  safe development runs, for example to force `mock` and `placeholder` without
  changing a production-bound spec. Use the exact flag names shown by `--help`;
  do not guess unsupported flags.
- If override flags are not available, set `provider = "mock"` and
  `model = "placeholder"` in the spec during development. Switch the spec to a
  production provider only after the user approves the cost and network use.
- Use `--force` only when the user wants to bypass the cache and refresh the
  artifact.

## How To Explain Results

Keep user summaries short and asset-oriented.

- Sidecar: `<output>.visura.json` records the resolved spec, compiled prompt,
  provider, model, render hash, output digest, references, cache decision, and
  timestamp.
- Cache: `.visura/cache/<hash>.<format>` stores content-addressed renders.
  `hit` means Visura restored an unchanged render; `miss` means it generated a
  new artifact; `refresh` means `--force` bypassed an existing cache entry.
- Status: `clean` means output, sidecar, cache, render hash, and output digest
  agree. `missing_output`, `missing_sidecar`, `stale`, `changed`, and `invalid`
  describe the one issue to fix next.
- User-facing summary example: "Rendered `assets/og-home.png` with `mock`.
  Cache was `miss`, sidecar is `assets/og-home.visura.json`, and status is now
  `clean`."

## Complete Example

Natural language request:

> Make an OG image for this page.

Agent interpretation:

- Use the existing page/product name and value proposition from the repo.
- Because the request says "for this page," treat the image as intended for that
  page. After render and status, update page metadata or docs references if
  those files are in scope; otherwise report that the image is ready but not
  wired.
- Use a local mock render first.

Spec: `assets/og-home.visura.toml`

```toml
kind = "poster"
provider = "mock"
model = "placeholder"
size = "1200x630"
quality = "draft"
output_format = "png"

[output]
path = "assets/og-home.png"
alt = "Open graph image for the Visura home page showing declarative image generation specs."

[style]
medium = "clean product launch graphic"
mood = "technical, polished, accessible"
palette = ["ink black", "electric blue", "mint green", "white"]
notes = "Open graph composition with large readable title and simple symbolic asset blocks."

[content]
headline = "Visura"
subhead = "Declarative image assets for developer workflows"
visual = "layered TOML spec cards connected to a generated image preview and cache badge"
constraints = "1200 by 630 social preview, no tiny text, strong left-to-right hierarchy"
```

Commands:

```bash
uv run visura validate assets/og-home.visura.toml
uv run visura compile assets/og-home.visura.toml
uv run visura status assets/og-home.visura.toml
uv run visura render assets/og-home.visura.toml
uv run visura status assets/og-home.visura.toml
```

Expected validation output, abbreviated:

```json
{
  "kind": "poster",
  "provider": "mock",
  "model": "placeholder",
  "size": "1200x630",
  "output": {
    "path": "assets/og-home.png",
    "alt": "Open graph image for the Visura home page showing declarative image generation specs.",
    "name": null
  }
}
```

Expected compile output, abbreviated:

```json
{
  "kind": "poster",
  "provider": "mock",
  "model": "placeholder",
  "prompt": "Create a poster image. Medium: clean product launch graphic. Mood: technical, polished, accessible. Palette: ink black, electric blue, mint green, white. Style notes: Open graph composition with large readable title and simple symbolic asset blocks. Headline: Visura. Subhead: Declarative image assets for developer workflows. Visual: layered TOML spec cards connected to a generated image preview and cache badge. Constraints: 1200 by 630 social preview, no tiny text, strong left-to-right hierarchy.",
  "options": {
    "size": "1200x630",
    "output_format": "png",
    "quality": "draft"
  },
  "output": {
    "path": "assets/og-home.png",
    "alt": "Open graph image for the Visura home page showing declarative image generation specs.",
    "name": null
  }
}
```

Expected status before render, abbreviated:

```json
[
  {
    "spec_path": "assets/og-home.visura.toml",
    "ok": false,
    "state": "missing_output",
    "output_path": "assets/og-home.png",
    "sidecar_path": "assets/og-home.visura.json",
    "provider": "mock",
    "model": "placeholder",
    "kind": "poster",
    "output_exists": false,
    "sidecar_exists": false,
    "cache_exists": false
  }
]
```

Expected render output, abbreviated:

```json
{
  "spec_path": "assets/og-home.visura.toml",
  "output_path": "assets/og-home.png",
  "sidecar_path": "assets/og-home.visura.json",
  "provider": "mock",
  "model": "placeholder",
  "kind": "poster",
  "render_hash": "sha256:...",
  "output_digest": "sha256:...",
  "cache": "miss"
}
```

Expected status after render, abbreviated:

```json
[
  {
    "spec_path": "assets/og-home.visura.toml",
    "ok": true,
    "state": "clean",
    "output_exists": true,
    "sidecar_exists": true,
    "cache_exists": true,
    "current_render_hash": "sha256:...",
    "sidecar_render_hash": "sha256:..."
  }
]
```

Reference update:

- If app or docs files are in scope, update the page's OG image reference to
  `assets/og-home.png` and reuse the spec's `output.alt` text where the
  framework supports image alt metadata.
- If source edits are out of scope, do not touch them. Tell the user the asset
  is rendered and ready to wire.

Expected final agent summary:

"Created `assets/og-home.visura.toml` and rendered `assets/og-home.png` with
`mock`. Cache was `miss`, sidecar is `assets/og-home.visura.json`, and status
is `clean`. The page metadata now points at the new OG image."

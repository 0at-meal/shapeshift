# ADR-0001: Stack choice
Status: Accepted   Date: 2026-11-15

## Context

Shapeshift is a "micro-app generator": a user drops a CSV/JSON file and/or a document
corpus, and the system produces verified DuckDB SQL plus interactive React/ECharts
components, with no human frontend work. Phase 2 adds an AST firewall, an
execution-repair loop (converge within 2 retries) and a VLM layout critic. Quality is
measured on Spider/BIRD subsets.

Constraints gathered in the stack interview (2026-11-15):

| Topic | Answer | What it forces |
| --- | --- | --- |
| Purpose / team | Solo portfolio demo | Fewest moving parts; no ops burden |
| Strongest language | Python (the UI is TypeScript/React regardless) | Orchestration, validation and evals should be Python |
| Generated output | Real React/TSX code, not a declarative spec | A sandbox and a code firewall are core, not optional |
| Models | Provider-agnostic, hosted | An LLM interface with swappable adapters; a separate embeddings interface |
| Delivery | Standalone demo app first; embedding later | No packaging work (npm / script tag) in the MVP |
| Corpus | Full document corpus (parse, chunk, embed, retrieve) in the MVP | PDF parsing, an embedding model, vector search |
| Data sensitivity | Whatever visitors upload, possibly personal data | No-retention handling, minimised LLM payloads, a privacy notice |
| Hosting budget | Free tiers only | Static frontend, scale-to-zero backend, small memory, cold starts, no local disk |
| Persistence | Shareable links, no accounts | Server-side storage with expiry and abuse controls, but no auth or user database |
| Where data runs | Undecided | This ADR has to decide it |

Three of these pull against each other, and the options below differ mainly in how they
resolve them:

1. **Uploads may contain personal data, but the budget is free tier with no accounts.**
   Holding raw user files on a small, cold-starting server with no disk is both the
   riskiest and the least reliable place to put them.
2. **Python is the strongest language, but generated TSX has to be parsed, transpiled and
   run in a browser.** Something has to own the TypeScript-side tooling.
3. **Shareable links require server storage, even if everything else stays in the
   browser.** Sharing is the one point where user data must leave the device.

Two facts hold for every option and belong in the privacy notice: whatever is put in a
prompt (schema, column names, sample values, retrieved corpus chunks) goes to the LLM
provider; and generated code can be steered by prompt injection hidden in an uploaded
file or document, so it must be treated as hostile.

## Options considered

### Option A — Browser-executed data, stateless Python brain

- **Web**: Vite + React + TypeScript single-page app on a static host. DuckDB-WASM runs
  all SQL in the browser; raw rows never reach our server.
- **API**: FastAPI (Python, `uv`), stateless. Owns prompt construction, the LLM and
  embedding adapters, SQL validation with `sqlglot` (parse, qualify against the uploaded
  schema, SELECT-only), the TSX firewall (tree-sitter TypeScript grammar from Python), and
  share-link storage.
- **Repair loop**: split. The server proposes SQL/TSX; the browser executes it and posts
  back the DuckDB or runtime error; the server repairs. Loop state lives in the client, so
  the server can scale to zero between calls.
- **Generated code**: transpiled in the browser (sucrase or esbuild-wasm) and mounted in
  an `<iframe sandbox="allow-scripts">` with an opaque origin and a CSP that allows no
  network. It talks to the host only through a narrow `postMessage` protocol and can only
  run queries the server validated at generation time (by id, with bound parameters).
- **Corpus**: the server parses and chunks documents in memory, embeds them through the
  embeddings adapter, and returns chunks plus vectors to the browser, which stores them in
  DuckDB-WASM and retrieves by cosine similarity. Nothing is persisted server-side.
- **Layout critic**: screenshots are captured client-side (ECharts `getDataURL()`, or an
  HTML-to-image capture inside the sandbox) and sent to a vision model. No headless
  browser in production; Playwright runs only locally and in CI.
- **Share links**: on an explicit "share" action the browser uploads the
  server-signed code plus a Parquet slice of only the columns the dashboard uses, to
  object storage with an expiry. Viewers load the slice into their own DuckDB-WASM.
- **Evals**: a Python harness using native DuckDB and the same validation and repair
  modules the API imports.

Pros: raw uploads stay on the user's device, which is the strongest answer to "whatever
users upload"; the stateless API fits free scale-to-zero hosting; all reasoning, guard and
eval code is Python; in-browser analytics is a strong demo point.
Cons: the repair loop crosses the network on every retry; two toolchains (pnpm and uv);
production runs DuckDB-WASM while evals run native DuckDB, so versions must be pinned
together and a small parity test kept; browser memory caps file size (practically a few
hundred MB); the TSX firewall is written in Python against a syntax tree with no scope or
type information.

### Option B — Server-side Python, thin React renderer

- **Web**: the same Vite + React app, but only an upload form, a renderer and the sandbox
  iframe.
- **API**: FastAPI with native DuckDB. Uploads are held in server memory or temp storage
  for the session. Generation, execution, repair, corpus pipeline (with DuckDB's `vss`
  extension available) and evals all run in one Python process.

Pros: the simplest thing to build; the repair loop is a plain in-process `for` loop; the
eval harness and production use the identical code path and engine; it plays entirely to
the Python strength; share links are trivial because the data is already server-side.
Cons: raw visitor files, possibly containing personal data, sit on our server, which
turns retention, deletion and breach exposure into real obligations; free-tier containers
have little memory and lose in-memory sessions on every cold start or scale-down, and
generally have no persistent disk, so sessions need external storage anyway; a public,
account-less upload endpoint is an abuse magnet.

### Option C — All-TypeScript at the edge

- **Web + API**: one TypeScript monorepo. React app plus an edge-function API (for
  example Hono on Cloudflare Workers) with a provider-agnostic LLM SDK. DuckDB-WASM in
  the browser as in Option A. The TSX firewall uses the TypeScript compiler API or Babel,
  the natural home for it. Key-value and object storage on the same platform for share
  links.

Pros: one language and one toolchain; the best fit for free tiers (no container, no cold
starts to speak of); first-class TSX parsing and transpiling.
Cons: it is not the strongest language of the only developer; the SQL tooling is weaker
(no `sqlglot` equivalent with full DuckDB dialect support); Spider/BIRD tooling and the
wider eval ecosystem are Python, so a Python harness appears anyway and the validation
logic is then implemented twice or evaluated out-of-process; document parsing inside
edge-function limits is awkward.

### Comparison

| Criterion | A: browser data + Python brain | B: server-side Python | C: all-TypeScript edge |
| --- | --- | --- | --- |
| Raw uploads leave the device | No (only on explicit share) | Yes, always | No (only on explicit share) |
| Fit to free tiers | Good (stateless, scale-to-zero) | Poor (stateful, memory-bound) | Best |
| Fit to Python strength | Good | Best | Poor |
| Repair-loop simplicity | Medium (client/server round trips) | Best (in-process) | Medium |
| Eval harness shares production code | Yes (validation, repair, prompts) | Yes (everything) | Only if evals are also TypeScript |
| TSX tooling | Adequate (tree-sitter + browser transpile) | Adequate (same) | Best |
| Threat-model size | Medium | Largest | Medium |
| Build effort for one person | Medium | Lowest | Medium-high |

## Decision

**Option A**, accepted 2026-11-15.

It is the only option that satisfies "whatever users upload", "free tiers only" and
"Python strongest" at the same time. Option B is easier to build but spends its
simplicity on exactly the two things the constraints rule out: holding strangers' raw
files, and keeping state on a server that is not allowed to cost anything. Option C wins
on hosting and TSX tooling but moves the hardest logic (SQL grounding, repair, evals) out
of the developer's strongest language.

Decisions that come with Option A:

- **Rows stay in the browser by default.** Prompts carry the schema and a column profile
  (types, ranges, distinct counts); raw sample values are opt-in.
- **The sandbox is the security boundary; the AST firewall is defence in depth.** Static
  analysis of JavaScript can be evaded (computed property access, string-built
  identifiers), so nothing may depend on the firewall alone.
- **The server signs what it validates.** Generated code is HMAC-signed after passing the
  firewall, and the share endpoint accepts only signed code, so a client cannot publish
  arbitrary script under our domain.
- **LLM access goes through a small in-house interface** with one adapter per provider
  over the official SDKs, plus a separate embeddings interface. This keeps the dependency
  surface small and makes per-provider eval comparisons a configuration change.
- **Monorepo layout**: `apps/web` (pnpm), `apps/api` (uv), `bench/` (Python, imports
  from `apps/api`). TypeScript API types are generated from FastAPI's OpenAPI schema.
- **Root `package.json` scripts are the single entry point** for every command, so they
  work unchanged in PowerShell, bash and CI.

Placeholder values this sets (filled into CLAUDE.md, .claude/, .github/ on acceptance; the
scripts themselves arrive with the repo skeleton in the first feature plan):
| Placeholder | Value |
| --- | --- |
| {{INSTALL_CMD}} | `pnpm run setup` (runs `pnpm install` and `uv sync --project apps/api`) |
| {{RUN_CMD}} | `pnpm dev` (Vite dev server and `uvicorn --reload` together) |
| {{TEST_CMD}} | `pnpm test` (`vitest run` and `uv run pytest`) |
| {{LINT_CMD}} | `pnpm lint` (`biome check` and `ruff check`) |
| {{TYPECHECK_CMD}} | `pnpm typecheck` (`tsc --noEmit` and `mypy`) |
| {{FORMAT_CMD}} | `pnpm format` (`biome format --write` and `ruff format`) |
| {{VERIFY_CMD}} | `pnpm verify` (lint, typecheck, test, in that order) |
| {{COVERAGE_CMD}} | `pnpm coverage` (`vitest run --coverage` and `pytest --cov`) |
| {{AUDIT_CMD}} | `pnpm audit:deps` (`pnpm audit` and `uv run pip-audit`) |

## Consequences

Becomes easy:
- A credible privacy statement: raw files are processed on the user's device.
- Free hosting: a static site plus a stateless container that can sleep.
- Evals: the Python harness imports the production validation and repair code directly.
- Swapping or comparing model providers.

Becomes hard, and must be planned for:
- **Cost abuse.** A public demo with no accounts spends our API keys. It needs per-IP
  rate limits and a hard daily spend cap from day one.
- **Share links are the one path where user data reaches our storage.** They need
  explicit consent in the UI, a size cap, unguessable ids, automatic expiry and a delete
  link. This goes into `docs/threat-model.md` with the first feature that touches it.
- **Documents pass through the API and the embedding provider** even though table rows do
  not. They are processed in memory and never stored or logged. An in-browser embedding
  model is a possible later upgrade to close this gap.
- **Engine parity.** DuckDB-WASM and native DuckDB versions are pinned together, with a
  test that runs a fixed query set on both.
- **Spider/BIRD are SQLite benchmarks.** Their gold SQL is SQLite dialect, so execution
  accuracy must compare result sets (gold run on SQLite, prediction run on DuckDB over the
  same data), and dialect differences will cost some points that are not model errors.
- **Every repair retry is a network round trip**, so the 2-retry convergence target is
  also a latency budget.
- **Embedding later** (script tag or npm package) will need its own ADR; the sandbox
  iframe design is intended to carry over.

Still to verify (not checked while drafting; revisit this ADR if any of them fails):
- Current free-tier terms for the hosting candidates: a static host (Cloudflare Pages,
  Vercel or Netlify), a scale-to-zero container host (Google Cloud Run, Render or Hugging
  Face Spaces), and S3-compatible object storage with lifecycle expiry.
- A one-day spike: DuckDB-WASM loading a 100 MB CSV, cosine similarity over a few
  thousand stored vectors, and a sandboxed iframe rendering transpiled TSX with ECharts
  under a no-network CSP.
- That the tree-sitter TypeScript grammar is sufficient for the import allowlist and
  banned-identifier rules the firewall needs.

## Amendments
2026-11-15, from the F-001 spec (conflicts 1 and 4):
- The Spider/BIRD harness lives in `bench/`, not `evals/`. `evals/` is kept for tests of
  the agent's own configuration (CLAUDE.md, skills, hooks), as the SDLC playbook uses it.
- "Raw sample values are opt-in" is narrowed. By default prompts also carry the distinct
  values of text columns that have 20 or fewer of them, skipping columns that look
  personal. Raw rows stay opt-in. Filters such as `status = 'Shipped'` are wrong without
  the values.
- Model providers are used on free API tiers, so limits are counted in tokens, not money.

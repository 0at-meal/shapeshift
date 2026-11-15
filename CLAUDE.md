# Shapeshift — agent guide

## Commands
All commands are root `package.json` scripts, so they run the same in PowerShell, bash and CI.
- Install: `pnpm run setup`
- Run locally: `pnpm dev`
- Test: `pnpm test`   Lint: `pnpm lint`   Types: `pnpm typecheck`
- Verify (must pass before "done"): `pnpm verify`

## Architecture (one paragraph)
Shapeshift turns a dropped CSV/JSON file or document corpus into verified DuckDB SQL plus
generated React/ECharts components. `apps/web` is a Vite + React + TypeScript app that runs
all SQL in the browser with DuckDB-WASM, so raw rows stay on the user's device, and mounts
generated TSX in a sandboxed, no-network iframe. `apps/api` is a stateless FastAPI service
that builds prompts, calls models through provider-agnostic LLM and embedding adapters,
validates SQL with sqlglot, checks generated TSX with an AST firewall, signs what it
validates, and stores share links with an expiry. `bench/` is a Python harness that runs
the API's validation and repair code against Spider and BIRD. The sandbox is the security boundary; the firewall is
defence in depth — see docs/adr/.

## Workflow rules
- Never write code without an accepted plan.md for the feature.
- Feature docs live in docs/features/F-xxx-<slug>/ (intent.md, spec.md, plan.md). Copy from docs/features/_template/.
- Tests are named after the requirement they prove: test_req_<id>_<behaviour>.
- During bug fixes, write a failing test first; never edit a locked test (.claude/locked-tests.txt).
- Update docs and docs/threat-model.md in the same PR as the code.
- Never log personal data. Never read or print secrets.

## Definition of done
Verify passes, every REQ in scope has a test, reviewer + security-auditor subagents run, PR lists REQ IDs.

## Mistakes not to repeat
- (add one line each time a mistake happens twice)

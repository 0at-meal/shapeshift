# F-001 — Plan   (links: spec.md)

Status: accepted on 2026-11-15, from a plan-mode session against the accepted spec.

## Context
The intent and the spec for F-001 (the whole micro-app generator platform, 49
requirements) are accepted. The repository holds only the SDLC scaffold and documents:
there is no code, so `pnpm verify`, the stop hook and CI all fail today. This plan says
how the platform gets built, in what order, and what proves each requirement.

Decisions from the plan-mode interview (2026-11-15):
- The build lands as a **series of pull requests** in a fixed order. This is build order
  only. Nothing is deployed publicly until the last one.
- Model providers: **Gemini** (generation, vision, embeddings) and **Groq** (second
  generation provider), both on free tiers.
- Hosting is **chosen after a check** of current free-tier terms, recorded as ADR-0002
  for acceptance before any deploy work.

Machine state checked: Node 26.1, pnpm 12.21, uv 0.13.8, Python 3.13, Docker 29.6 are
installed. Nothing needs installing globally.

## Target layout
```
package.json  pnpm-workspace.yaml  biome.json  .gitattributes  README.md
apps/web/src/
  data/      DuckDB-WASM engine (external access off), ingest, profiling
  generate/  API client, repair-loop state machine
  sandbox/   iframe host, message protocol, in-iframe runtime (React, ECharts, SDK)
  corpus/    passage store in DuckDB, retrieval, citations
  critic/    screenshot capture, verdict handling
  share/     consent dialog, Parquet slice export, viewer
  ui/        app shell, privacy notice, panels
apps/api/src/shapeshift_api/
  main.py  settings.py  request_log.py  signing.py
  llm/         provider protocol, gemini.py, groq.py, fake.py, token budget
  embeddings/  protocol, gemini.py
  sqlguard/    sqlglot validation, query registry
  firewall/    tree-sitter TSX checks, rules
  generate/    prompts, pipeline, repair
  corpus/      parse, chunk, routes
  critic/      rubric, routes
  share/       store (local folder and S3-compatible), routes
  limits/      hashed per-visitor counters, shared pool
bench/         harness, dataset download scripts, fixed test sets, results/
e2e/           Playwright tests that need a real browser
```
Root `package.json` scripts stay the single entry point (ADR-0001). `bench/` is a second
uv project that depends on `apps/api` by path, so benchmarks import production code.

## Steps (in order)
Each step is one pull request that lists its REQ IDs, passes `pnpm verify`, updates
`docs/threat-model.md` for the threats it closes, and gets the reviewer and
security-auditor subagents before it is opened.

**0. Plan and document fixes** (no code)
- Commit this plan. Amend ADR-0001 (harness is `bench/`, not `evals/`; short value lists
  sent by default, per spec conflict 1). Fix the same wording in `CLAUDE.md`.

**1. Checks, skeleton and gates** — REQ-001.39
- Checks first, in scratch code that is not merged: DuckDB-WASM with a 100 MB CSV and
  with external access switched off; a sandboxed iframe rendering transpiled TSX and
  ECharts under a no-network policy in Chrome, Firefox and Safari; the tree-sitter
  TypeScript grammar against the firewall's rules; official free-tier quotas and data
  terms for Gemini and Groq; current free-tier terms for hosting.
- Outputs: `docs/adr/0002-hosting-and-providers.md` (for acceptance) and the "still to
  verify" list in ADR-0001 closed out. If a check fails a spec limit, the spec is amended
  before step 2.
- Skeleton: root scripts, `apps/web` shell, `apps/api` with `/healthz`, allowlist request
  logging, `.gitattributes`.
- Gates: CI gains a Playwright job and frozen installs; the post-edit format hook becomes
  file-scoped (formats only the edited file); `pnpm verify` stays lint, types and unit
  tests so the stop hook stays fast.
- After this step the stop hook and CI are green.

**2. Data in** — REQ-001.1, .2, .3, .4, .14, .16, .40, .48
- `apps/web/src/data/`, `ui/` (drop zone, table list, privacy notice), a seeded generator
  for the made-up store dataset and its metrics handbook, the engine-parity query set.

**3. Model layer and limits** — REQ-001.36, .41, .42
- `llm/`, `embeddings/`, `limits/`. A deterministic fake provider for tests. Token
  accounting per request, per visitor per day and for the shared pool. Clean handling of
  provider quota errors.

**4. SQL path** — REQ-001.11 (SQL half), .12, .13, .15 (server half), .17 (SQL), .24, .27, .37, .38
- `sqlguard/`, `generate/`, `apps/web/src/generate/`. A request returns validated SQL, the
  browser runs it and shows a plain table. Repair on validation or execution errors.

**5. SQL benchmarks** — REQ-001.43, .44, .45, .47, .49
- `bench/`: download scripts for BIRD Mini-Dev and Spider (data is not committed),
  reference answers on SQLite, predictions on DuckDB over the same data, with and without
  knowledge, resumable daily allowance, dated results file. Placed here so prompt work in
  later steps is measured, not guessed.

**6. Sandbox, firewall and generated components** — REQ-001.11, .15, .18, .19, .20, .21, .22, .23, .25, .26, .46 (firewall and render sets)
- `sandbox/`, `firewall/`, `signing.py`, component generation and repair, honest failure
  display. Containment proven in Playwright with a malicious component that skips the
  firewall. This is the riskiest step.

**7. Knowledge corpus** — REQ-001.5, .6, .7, .8, .9, .10, .17 (passages)
- `corpus/` on both sides: parse, chunk and embed in memory on the API; store, retrieve
  and cite in the browser.

**8. Layout critic** — REQ-001.28, .29, .30, .46 (critic set)
- `critic/` on both sides, with the seeded-defect chart set added to `bench/`.

**9. Sharing** — REQ-001.31, .32, .33, .34, .35
- `share/` on both sides. Local-folder storage for development and tests; S3-compatible
  storage for production.

**10. Deploy and full runs** — closes REQ-001.40 (final notice text), all targets
- Implement ADR-0002: container image, deploy configuration, production security
  headers, shared-pool size. Run the full benchmarks over several days and commit the
  results against the intent's targets. Final README and threat model. Name the metric
  in `ops/bands.yaml`.

When implementation departs from this plan, `plan.md` is updated in the same commit.

## Tests that prove it
Runners: P = pytest, V = Vitest, E = Playwright.

| REQ ID | Test name | Runner | Step |
| --- | --- | --- | --- |
| REQ-001.1 | `test_req_001_1_csv_and_json_become_tables_without_network` | V, E | 2 |
| REQ-001.2 | `test_req_001_2_bad_or_oversized_file_refused_no_partial_table` | V | 2 |
| REQ-001.3 | `test_req_001_3_profile_has_types_nulls_distinct_min_max` | V | 2 |
| REQ-001.4 | `test_req_001_4_sample_dataset_loads_in_one_click` | E | 2 |
| REQ-001.5 | `test_req_001_5_pdf_md_txt_parsed_chunked_embedded` | P | 7 |
| REQ-001.6 | `test_req_001_6_docx_processed_like_other_formats` | P | 7 |
| REQ-001.7 | `test_req_001_7_document_content_not_retained_or_logged` | P | 7 |
| REQ-001.8 | `test_req_001_8_scanned_encrypted_or_oversized_doc_refused` | P | 7 |
| REQ-001.9 | `test_req_001_9_relevant_passages_retrieved_and_listed` | V | 7 |
| REQ-001.10 | `test_req_001_10_generation_works_without_corpus` | P, V | 7 |
| REQ-001.11 | `test_req_001_11_request_produces_dashboard_with_progress` | E | 4, 6 |
| REQ-001.12 | `test_req_001_12_sql_with_unknown_table_or_column_rejected` | P | 4 |
| REQ-001.13 | `test_req_001_13_non_select_and_file_network_functions_rejected` | P | 4 |
| REQ-001.14 | `test_req_001_14_engine_blocks_external_access` | E | 2 |
| REQ-001.15 | `test_req_001_15_component_can_only_run_registered_queries` | P, V | 4, 6 |
| REQ-001.16 | `test_req_001_16_query_timeout_and_row_cap_enforced` | V | 2 |
| REQ-001.17 | `test_req_001_17_details_show_sql_and_passages` | V | 4, 7 |
| REQ-001.18 | `test_req_001_18_followup_request_keeps_working_components` | V | 6 |
| REQ-001.19 | `test_req_001_19_controls_update_view_without_model_call` | E | 6 |
| REQ-001.20 | `test_req_001_20_firewall_rejects_each_banned_construct_with_rule` | P | 6 |
| REQ-001.21 | `test_req_001_21_malicious_component_cannot_reach_network_host_or_storage` | E | 6 |
| REQ-001.22 | `test_req_001_22_host_ignores_unknown_or_malformed_messages` | V | 6 |
| REQ-001.23 | `test_req_001_23_tampered_or_unsigned_code_refused` | P | 6 |
| REQ-001.24 | `test_req_001_24_sql_repair_revalidates_and_stops_after_two_retries` | P | 4 |
| REQ-001.25 | `test_req_001_25_component_repair_stops_after_two_retries` | P, V | 6 |
| REQ-001.26 | `test_req_001_26_failed_part_explained_working_parts_shown` | V | 6 |
| REQ-001.27 | `test_req_001_27_empty_result_shows_no_data_without_repair` | V | 4 |
| REQ-001.28 | `test_req_001_28_critic_returns_structured_verdict_for_screenshot` | P | 8 |
| REQ-001.29 | `test_req_001_29_revision_refirewalled_max_two_rounds` | P | 8 |
| REQ-001.30 | `test_req_001_30_critic_failure_or_timeout_never_blocks_dashboard` | V | 8 |
| REQ-001.31 | `test_req_001_31_nothing_uploaded_before_consent_and_confirmation` | V, E | 9 |
| REQ-001.32 | `test_req_001_32_share_returns_128bit_id_delete_link_7_day_expiry` | P | 9 |
| REQ-001.33 | `test_req_001_33_shared_dashboard_interactive_without_model_calls` | E | 9 |
| REQ-001.34 | `test_req_001_34_oversized_slice_or_bad_signature_refused` | P | 9 |
| REQ-001.35 | `test_req_001_35_deleted_or_expired_share_is_gone` | P | 9 |
| REQ-001.36 | `test_req_001_36_all_providers_pass_same_contract_tests` | P | 3 |
| REQ-001.37 | `test_req_001_37_prompt_payload_contains_only_permitted_fields` | P | 4 |
| REQ-001.38 | `test_req_001_38_injected_instructions_marked_as_data_and_still_validated` | P | 4 |
| REQ-001.39 | `test_req_001_39_logs_contain_only_allowlisted_fields` | P | 1 |
| REQ-001.40 | `test_req_001_40_upload_disabled_until_notice_acknowledged` | V | 2 |
| REQ-001.41 | `test_req_001_41_token_limits_per_request_visitor_and_pool` | P | 3 |
| REQ-001.42 | `test_req_001_42_provider_quota_exhaustion_shows_message_no_partial_result` | P, V | 3 |
| REQ-001.43 | `test_req_001_43_harness_uses_production_pipeline_duckdb_vs_sqlite_gold` | P | 5 |
| REQ-001.44 | `test_req_001_44_reports_with_and_without_knowledge_scores` | P | 5 |
| REQ-001.45 | `test_req_001_45_reports_first_pass_failures_and_repaired_share` | P | 5 |
| REQ-001.46 | `test_req_001_46_firewall_render_and_critic_sets_reported` | P | 6, 8 |
| REQ-001.47 | `test_req_001_47_results_file_written_with_targets` | P | 5 |
| REQ-001.48 | `test_req_001_48_wasm_and_native_results_match` | P, E | 2 |
| REQ-001.49 | `test_req_001_49_run_stops_at_allowance_and_resumes_without_repeats` | P | 5 |

Unit tests never call a real model: they use the fake provider or recorded responses.
Real calls happen only in `bench/` and in a manual live smoke command.

## Risks and how each is handled
- **Step 6 is the riskiest.** Sandbox behaviour differs between browsers, and static
  checks on JavaScript can be evaded. Handled by checking the sandbox in three browsers in
  step 1, and by the Playwright test that runs hostile code with the firewall bypassed.
- **Groq's free tier may have no usable vision model.** The spec asks for two providers
  for generation and vision. If the step 1 check confirms this, the spec is amended to
  two for generation and one for vision before step 3, and you are asked.
- **Gemini's free tier uses submitted content to improve Google's products** (from
  secondary sources; confirmed or corrected in step 1). The privacy notice must say so.
  If the official terms turn out worse than that, it comes back to you.
- **Free quotas may be smaller than the limits in the spec.** The shared pool is a
  setting; benchmark runs resume across days.
- **DuckDB-WASM may not manage 100 MB files.** Checked in step 1; the limit in the spec
  is lowered if needed.
- **Benchmarks are SQLite, the app is DuckDB.** Reference answers run on SQLite and
  predictions on DuckDB over the same data, compared as result sets with fixed rules for
  ordering and number precision. Dialect losses are reported separately where visible.
- **A request must fit 100,000 tokens.** Prompts cap the number of columns and values
  described for very wide tables.
- **The stop hook slows as tests grow.** Playwright and benchmark runs stay out of
  `pnpm verify`; CI runs them.
- **The work is large for one person and one plan.** Each step is a reviewable pull
  request, and the plan is corrected in the same commit whenever the build departs from it.

Options considered and not taken: a declarative chart spec instead of generated code
(ruled out by the intent); compiling TSX on the server (needs Node in the API container,
so it is compiled in the browser instead); one pull request for everything (unreviewable).

## Rollout and rollback
- Steps 0 to 9 merge to `main` with nothing deployed. Rolling one back is reverting its
  pull request.
- Step 10 is the only deployment. Rollback is redeploying the previous image; shared
  dashboards expire on their own within 7 days.
- Before step 10 starts, ADR-0002 must be accepted.

## Out of this plan (deferred)
- Embedding in other sites, document chat, accounts, OCR for scanned PDFs.
- Tests of the agent's own configuration (`evals/` in the playbook's sense).
- Building dashboards on mobile.

## Verification
- Per step: `pnpm verify`, `pnpm e2e`, `pnpm coverage` (80% lines on both apps),
  `pnpm audit:deps`, then the reviewer and security-auditor subagents on the diff.
- From step 6: the demo scenario is walked through in a real browser (store dataset, the
  two requests in the intent), and the second public dataset is tried with no handbook.
- At the end: the committed benchmark results are compared against the eight targets in
  the intent, each marked met or not.

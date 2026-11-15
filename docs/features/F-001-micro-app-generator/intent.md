# F-001 — Micro-app generator platform   (Stage: Plan)
Author: Niraj (originator). Written up by Claude from the initial idea, the interview and
the originator's corrections, all on 2026-11-15. Status: accepted by the originator on
2026-11-15.

## Problem
Anyone who has data and wants to see it visualized has to wait on someone technical.
Non-technical teams constantly need custom interactive calculators, cohort visualizers or
data explorers, and wait weeks on engineering tickets for one-off internal tools. The
audience is broad: no particular industry or role.

## Outcome
The entire platform, built together as one feature. There is no prototype and no MVP
stage: nothing below ships without the rest.

A demo app where dropping any CSV/JSON or knowledge corpus generates verified DuckDB SQL
plus interactive React/ECharts visual components on the fly, protected and corrected by:
- an AST static-analysis firewall that blocks unsafe imports and mutations;
- an automated execution-repair loop;
- a layout-critic VLM check that screenshots rendered charts and fixes overlapping labels
  or bad axes.

It acts as a "micro-app generator" that turns raw data into live, verified interactive
dashboards without human frontend intervention.

### What the knowledge corpus is for
The corpus supplies the meaning that the data's column names do not carry. It is used to
ground the SQL and the calculators, in four ways:
- what columns and coded values mean ("type = 'OWNER' means the primary account holder");
- how metrics are calculated (the formula for margin, retention, a score);
- which everyday words map to which columns (synonyms and domain terms);
- conventions and tie-breakers (fiscal year, which date column counts, what to exclude).

This is grounded in published results, not assumed. On the BIRD benchmark the same model
scores about 13 points higher when given this kind of knowledge (ChatGPT: 37.2% with,
24.1% without, dev set). A 2026 paired study found a single 4 KB document of measures,
conventions and disambiguation rules added 17 to 23 points across three frontier models,
and that the document mattered more than which model was used.

The corpus is not a document question-answering feature. Documents are there to make the
dashboards correct, not to be chatted with.

### When repair does not converge
If a query or a component still fails after 2 retries, the user sees everything that did
succeed, and in place of the failed part a plain-language explanation of what could not be
built, with the option to rephrase the request or view the attempted SQL. Nothing
unverified is ever shown as if it were a result.

### How we will know it works
Initial targets, set by Claude at the originator's request; to be revisited after the
first full eval run.

| Measure | Target |
| --- | --- |
| SQL execution accuracy, BIRD Mini-Dev (500 questions, 2026 update), knowledge supplied as corpus | At least 70%, and no more than 10 points below the published score of the same model |
| Effect of the corpus: the same run with and without the knowledge | At least 10 points better with it |
| SQL execution accuracy, 200-question sample of the Spider dev set | At least 80% |
| Repair loop: queries that fail on first execution and run correctly within 2 retries | At least 80% |
| Generated components that render without error within 2 retries | At least 95% |
| Schema grounding: executed SQL that refers only to tables and columns in the dropped data | 100%, enforced, not sampled |
| Firewall: a fixed set of known-unsafe code samples that are blocked | 100% |
| Layout critic: seeded defects (overlapping labels, bad axes) that it detects | At least 80% |

For context, published scores on BIRD Mini-Dev as of 28 October 2026 put the strongest
models at 84% to 87% overall, and the full BIRD test leaderboard tops out at 83.4% against
a human score of 92.96%.

### Demo scenario
A made-up store dataset that anyone can follow and that contains no real people: orders,
customers and products as three CSV files, plus a two-page "metrics handbook" as the
corpus. The demo answers two requests:
- "Show how margin changed by category over the last year, and let me test what a 10%
  discount cap would do" (a data explorer plus a what-if calculator);
- "Group customers by the month of their first purchase and show how many came back" (a
  cohort visualizer).

A second, unrelated public dataset with no handbook is run alongside it, to show the app
is not tuned to one subject.

## Users and systems affected
- Anyone with data to visualize: they drop a file and get a dashboard, or open one
  somebody shared with them.
- The developer: one person builds and runs all of it.
- Systems: hosted model providers for generation, vision critique and embeddings; the
  visitor's browser (where the data is queried and generated code runs); a small API;
  storage for shared dashboards; the BIRD and Spider benchmark data.

## Constraints
- A solo portfolio project. Free hosting tiers only.
- Python is the strongest language; the UI is TypeScript/React.
- The model generates real React/TSX code, not a declarative chart spec.
- Models are hosted and provider-agnostic, so providers can be swapped and compared.
- A full document corpus (parse, chunk, embed, retrieve) is included.
- Visitors may upload anything, including personal data. Nothing personal is logged, and
  what is sent to model providers is kept to the minimum.
- Dashboards are shareable by link. There are no user accounts.
- No split into phases. The firewall, the repair loop, the layout critic and the evals are
  part of this feature, not follow-ups.
- The benchmarks are written for SQLite, while this app generates DuckDB SQL, so some
  lost points will be dialect differences and not model errors.
- The stack is fixed by ADR-0001 (docs/adr/0001-stack.md).

## Out of scope
- Embedding in other sites (script tag or npm package). A demo app only, for now.
- Asking questions of the documents themselves (document chat).
- Accounts, saved libraries, billing.

## Open questions
None. Three decisions above were delegated to Claude and accepted with this intent: the
behaviour when repair does not converge, the targets table, and the demo scenario.

## Sources
Read on 2026-11-15.
- BIRD benchmark, leaderboards and Mini-Dev: https://bird-bench.github.io/
- BIRD paper (Li et al., NeurIPS 2023): https://arxiv.org/abs/2305.03111
- Semantic layers paired benchmark (Rumiantsau and Fokeev, 2026): https://arxiv.org/abs/2604.25149
- Spider 2.0 (for the spec stage; includes DuckDB tasks): https://spider2-sql.github.io/
- The Spider 1.0 figure behind the 80% target comes from secondary summaries (86% to 91%
  reported for top systems) and was not checked against the official leaderboard.
- Related work worth reading at the spec stage: the BIRD group's GenUI-Agent and
  UX-Tau-Bench (May 2026), which evaluate agents that respond with generated UI code.

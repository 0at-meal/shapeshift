# F-001 — Spec   (links: intent.md)
Status: accepted by the product owner on 2026-11-15. Produced from the intent accepted
the same day, within ADR-0001. Skill applied: privacy-minors.

## Design
Three parts, as fixed by ADR-0001:

- **Web app** (`apps/web`). Holds the user's data in DuckDB-WASM, runs every query, and
  mounts generated components inside a sandboxed iframe. Raw rows never leave it, except
  through an explicit share.
- **API** (`apps/api`). Stateless. Builds prompts, calls model providers, validates SQL,
  runs the code firewall, signs what it validated, parses and embeds documents, and stores
  share links.
- **Benchmark harness** (`bench/`). Runs the API's own generation, validation and repair
  code against BIRD and Spider with native DuckDB.

One request flows like this:

1. The browser sends the request text, the schema, a column profile and the retrieved
   document passages. No rows.
2. The API asks the model for SQL plus a TSX component, then validates both. Anything that
   fails validation is repaired before it leaves the API.
3. The browser runs the SQL. Execution or render errors go back to the API for repair, at
   most twice.
4. The component renders in the sandbox. A screenshot goes to a vision model, which may
   request one revision.
5. The user sees the dashboard, the SQL behind it and the document passages used.

Generated code is treated as hostile at every step. The sandbox is the security boundary;
the SQL validator and the code firewall are additional layers, and none relies on the
model behaving.

## Requirements
All are Must unless marked Should. With no MVP stage, nothing here is optional at release.

### Data in
| ID | Requirement | Acceptance criteria (Given/When/Then) | Priority |
| --- | --- | --- | --- |
| REQ-001.1 | Dropped CSV and JSON files become queryable tables in the browser. | Given one or more valid CSV or JSON files, when they are dropped, then each appears as a table with its name, columns, inferred types and row count, and no file content is sent to any server. | Must |
| REQ-001.2 | Bad files are refused cleanly. | Given a file that is not CSV/JSON, is malformed, or exceeds the size limit (100 MB per file, 300 MB in total), when it is dropped, then a plain message says why and no partial table is created. | Must |
| REQ-001.3 | Each table gets a column profile used for prompting. | Given a loaded table, when profiling completes, then every column has type, share of nulls, distinct count and, for numbers and dates, minimum and maximum. | Must |
| REQ-001.4 | One-click sample data. | Given a first-time visitor, when they choose the sample, then the made-up store dataset (three CSV files and the metrics handbook) loads with no upload. | Must |

### Knowledge corpus
| ID | Requirement | Acceptance criteria (Given/When/Then) | Priority |
| --- | --- | --- | --- |
| REQ-001.5 | Dropped documents become a searchable corpus. | Given PDF, Markdown or plain-text documents (up to 10 MB each, 20 documents), when they are dropped, then each is parsed, split into passages and embedded, and listed with its name and passage count. | Must |
| REQ-001.6 | Word documents are accepted too. | Given a .docx file within the same limits, when it is dropped, then it is processed like the other formats. | Should |
| REQ-001.7 | Documents are never kept by the server. | Given a document sent for processing, when the response has been returned, then no copy of its content, passages or vectors exists on the server or in any log. | Must |
| REQ-001.8 | Unreadable documents are refused cleanly. | Given a scanned PDF with no text layer, an encrypted file or one that exceeds the page or time limit, when it is dropped, then a plain message says why and nothing is added. | Must |
| REQ-001.9 | Relevant passages ground each request. | Given a corpus and a request, when generation starts, then the most relevant passages are retrieved in the browser and included in the prompt, and the finished dashboard lists the passages that were used. | Must |
| REQ-001.10 | The app works with no corpus. | Given only data files, when a request is made, then a dashboard is generated with no error about missing documents. | Must |

### Ask and generate
| ID | Requirement | Acceptance criteria (Given/When/Then) | Priority |
| --- | --- | --- | --- |
| REQ-001.11 | A plain-language request produces a dashboard. | Given loaded data, when the user describes what they want, then a dashboard of one or more interactive components appears, with visible progress while it is built. | Must |
| REQ-001.12 | Generated SQL is schema-grounded. | Given generated SQL, when it is validated, then it is accepted only if it parses as DuckDB SQL and every table and column it names exists in the loaded data; otherwise it is never executed. | Must |
| REQ-001.13 | Generated SQL can only read the loaded tables. | Given generated SQL, when it is validated, then anything other than a single SELECT is rejected, as is any function that reads files, reaches the network, loads extensions or changes settings. | Must |
| REQ-001.14 | The query engine itself cannot reach outside. | Given the in-browser database, when any query runs, then external file and network access is disabled at engine level, so a query that slipped past validation still cannot fetch or send anything. | Must |
| REQ-001.15 | Components can only run approved queries. | Given a rendered component, when it asks for data, then it may only name a query that was validated for that dashboard and supply typed parameters; it cannot submit SQL text. | Must |
| REQ-001.16 | Queries are bounded. | Given any query, when it runs longer than 10 seconds or returns more than 10,000 rows to a component, then it is stopped or truncated, and the user is told. | Must |
| REQ-001.17 | The work is inspectable. | Given a finished dashboard, when the user opens a component's details, then they see the SQL it runs and the document passages that informed it. | Must |
| REQ-001.18 | A dashboard can be extended by further requests. | Given an existing dashboard, when the user makes another request, then components are added or changed without losing the ones that already work. | Should |

### Generated components and their containment
| ID | Requirement | Acceptance criteria (Given/When/Then) | Priority |
| --- | --- | --- | --- |
| REQ-001.19 | Components are real, interactive React/ECharts code. | Given a request that needs a calculator, a cohort view or an explorer, when the dashboard renders, then its controls (sliders, dropdowns, filters) change what is shown without a new model call. | Must |
| REQ-001.20 | The code firewall blocks unsafe code before it reaches a browser. | Given generated TSX, when it is checked, then it is rejected if it imports anything outside the allowlist, or uses network APIs, dynamic code execution, storage or cookies, access to the parent window, navigation, or raw HTML injection; each rejection states the rule broken. | Must |
| REQ-001.21 | Components run in a sandbox that holds even if the firewall is bypassed. | Given a deliberately malicious component placed directly in the sandbox, when it runs, then it cannot make a network request, read or change the host page, or read storage or cookies. | Must |
| REQ-001.22 | The sandbox speaks a narrow, checked protocol. | Given any message from the sandbox, when the host receives it, then it is acted on only if it is one of the defined message types with a valid shape; everything else is ignored. | Must |
| REQ-001.23 | The server signs what it validated. | Given code and queries that passed validation, when they are returned, then they carry a server signature, and any later request to store them is refused if the signature does not match. | Must |

### Repair
| ID | Requirement | Acceptance criteria (Given/When/Then) | Priority |
| --- | --- | --- | --- |
| REQ-001.24 | SQL is repaired automatically, at most twice. | Given SQL that fails validation or execution, when repair runs, then the model receives the error and the query, each new attempt is validated again, and there are never more than 2 retries. | Must |
| REQ-001.25 | Components are repaired automatically, at most twice. | Given a component that is rejected by the firewall, fails to compile, throws while rendering or does not render within the time limit, when repair runs, then the same rule applies: error fed back, re-checked, at most 2 retries. | Must |
| REQ-001.26 | Failure is shown honestly. | Given a part that still fails after 2 retries, when the dashboard is shown, then the working parts appear as normal and the failed part shows a plain explanation, the option to rephrase and the attempted SQL; no unverified output is shown as a result. | Must |
| REQ-001.27 | No rows is an answer, not an error. | Given a valid query that returns nothing, when the component renders, then it says no data matched and no repair is triggered. | Must |

### Layout critic
| ID | Requirement | Acceptance criteria (Given/When/Then) | Priority |
| --- | --- | --- | --- |
| REQ-001.28 | Rendered charts are checked by a vision model. | Given a rendered component, when the visual check runs, then a screenshot taken in the browser is judged against a fixed list of defects (overlapping labels, clipped text, unreadable or misleading axes, empty chart, legend overflow) and the verdict is structured, not free text. | Must |
| REQ-001.29 | Defects lead to a revision that is checked like any other code. | Given a verdict listing defects, when a revision is generated, then it passes the firewall again before rendering, and there are at most 2 revision rounds. | Must |
| REQ-001.30 | The critic can never block a working dashboard. | Given the visual check fails, times out (20 seconds) or is switched off, when the dashboard is shown, then the working component is displayed as it is. | Must |

### Sharing
| ID | Requirement | Acceptance criteria (Given/When/Then) | Priority |
| --- | --- | --- | --- |
| REQ-001.31 | Sharing is explicit and informed. | Given a dashboard, when the user chooses to share, then a dialog states exactly what will be uploaded (the code, the queries, and only the columns the dashboard uses), that anyone with the link can see it, and when it expires; nothing is uploaded until they confirm, and confirming requires ticking a statement that the shared data contains no personal data about other people. | Must |
| REQ-001.32 | A share produces an unguessable link and a private delete link. | Given a confirmed share, when it completes, then the user gets a view link with at least 128 bits of randomness and a separate delete link, and the share expires after 7 days. | Must |
| REQ-001.33 | A shared dashboard is fully interactive for viewers. | Given a valid view link, when it is opened, then the dashboard renders in the same sandbox with the shared data loaded in the viewer's browser, all controls work, and no model is called. | Must |
| REQ-001.34 | Shares are bounded and verified. | Given a share request, when the data exceeds 10 MB or the code's signature is invalid, then it is refused with a reason. | Must |
| REQ-001.35 | Deleted and expired shares are gone. | Given a delete link is used or 7 days pass, when the view link is opened, then a not-found page is shown and the code and data no longer exist in storage. | Must |

### Models, privacy and cost
| ID | Requirement | Acceptance criteria (Given/When/Then) | Priority |
| --- | --- | --- | --- |
| REQ-001.36 | Model providers are swappable by configuration. | Given at least two generation and vision providers and one embeddings provider, when configuration changes, then the app and the benchmarks run on the other provider with no code change, and all providers pass the same contract tests. | Must |
| REQ-001.37 | Prompts carry the minimum. | Given any model call, when the outgoing payload is inspected, then it contains only the request text, schema, column profile, permitted value lists and retrieved passages; raw rows are included only if the user switched that on. | Must |
| REQ-001.38 | Uploaded content cannot give orders. | Given a data value or document passage that contains instructions, when it is placed in a prompt, then it is marked as data, and whatever the model returns still passes through the validator, firewall and sandbox. | Must |
| REQ-001.39 | Nothing personal is logged. | Given any request, when logs are written, then they contain only route, status, duration, model name, token counts, retry counts and outcome codes; no client address, request text, file or column names, data values, document text or prompts. | Must |
| REQ-001.40 | Visitors are told where data goes before they upload. | Given a first visit, when the app opens, then a notice explains what stays in the browser, what is sent to model providers (including screenshots), which provider is in use and how it may use what it receives, and what sharing does; uploading is enabled once it is acknowledged. | Must |
| REQ-001.41 | Model usage is capped in tokens. | Given a request has used 100,000 combined input and output tokens or 8 model calls, when it would make another call, then it stops and the failed parts are shown as REQ-001.26 describes. Given a visitor has used 100,000 tokens in a day, or the shared daily pool for the whole demo (a configured number) is used up, when another generation is requested, then it is refused with a plain message saying when it resets. | Must |
| REQ-001.42 | Running out of the provider's free quota is handled, not crashed on. | Given the model provider refuses a call because its quota or rate limit is exhausted, when that happens mid-request, then the user gets a plain message that the demo's allowance is used up for now, and nothing half-built is shown as a result. | Must |

### Benchmarks
| ID | Requirement | Acceptance criteria (Given/When/Then) | Priority |
| --- | --- | --- | --- |
| REQ-001.43 | One command measures SQL accuracy on the production code path. | Given the benchmark data, when the harness runs, then BIRD Mini-Dev (500 questions) and a fixed 200-question Spider dev sample go through the same generation, validation and repair code the API uses, with predictions run on DuckDB and reference answers on SQLite over the same data, and execution accuracy is reported per provider. | Must |
| REQ-001.44 | The corpus effect is measured. | Given BIRD Mini-Dev, when the harness runs with and without the benchmark's knowledge supplied as corpus, then both scores and their difference are reported. | Must |
| REQ-001.45 | Repair is measured. | Given a benchmark run, when it finishes, then it reports how many queries failed first time and what share ran correctly within 2 retries. | Must |
| REQ-001.46 | The firewall, the renderer and the critic each have a fixed test set. | Given the three sets (known-unsafe code samples, dashboard requests over the sample data, charts with seeded defects), when the harness runs, then it reports the share blocked, the share rendered within 2 retries, and the share of defects detected, plus the firewall's false-rejection rate on safe code. | Must |
| REQ-001.47 | Results are kept. | Given a completed run, when it ends, then a dated results file with model names, scores and the intent's targets (met or not) is written for committing. | Must |
| REQ-001.48 | Browser and benchmark engines agree. | Given a fixed set of queries, when they run on DuckDB-WASM and on native DuckDB, then the results match. | Must |
| REQ-001.49 | Benchmark runs have their own token allowance and can resume. | Given a configured daily token allowance for benchmarks (separate from the demo's limits), when a run reaches it or the provider's quota runs out, then the run stops cleanly with its progress saved; and when it is started again, then it continues from the next unanswered question without repeating or losing any. | Must |

## Non-functional targets
- **Speed.** Request to rendered dashboard: half within 30 seconds, nine in ten within 90
  seconds including repair. A 100 MB CSV loads within 30 seconds on a typical laptop. A
  shared link opens within 5 seconds.
- **Cold start.** The API may sleep. The app shows a "waking up" state and tolerates up to
  60 seconds.
- **Availability.** Free tiers, no commitment. The app degrades clearly when the API or a
  provider is down; data already loaded stays usable.
- **Accessibility.** The host interface is fully keyboard-operable and meets WCAG AA
  contrast. Every chart has a text title and a "view as table" alternative.
- **Browsers.** Current desktop Chrome, Edge, Firefox and Safari. Shared links are
  readable on mobile; building dashboards on mobile is not a goal.
- **Quality.** The eight targets in the intent's table.

The size, speed and row limits above are assumptions until ADR-0001's spike confirms what
DuckDB-WASM manages in practice.

## Data model changes
There is no database and there are no accounts or cookies.

| Data | Where | Personal data? | Retention and delete path |
| --- | --- | --- | --- |
| Loaded tables, column profiles, document passages and vectors | Browser memory only | Possibly, it is whatever the user dropped | Gone when the tab closes |
| Notice acknowledged (a flag) | Browser local storage | No | Until the user clears it |
| Share record: id, signed code, queries, data slice of used columns, created and expiry times, hash of the delete token | Object storage | Possibly, inside the data slice | 7 days, or at once via the delete link |
| Rate-limit counters keyed by a salted hash of the client address | API memory | Pseudonymous | 24 hours at most; lost on restart; never logged |
| Daily token totals: one per visitor (same salted hash) and one shared pool for the whole demo | API memory, or a single stored counter for the shared pool | Pseudonymous for the per-visitor totals | Reset daily; never logged |
| Benchmark progress: which questions are answered, with predictions and scores | Local files on the developer's machine | No, benchmark data only | Kept until the run's results are written |

## Threats and privacy
To be mirrored into `docs/threat-model.md` with the implementation.

| ID | Threat (STRIDE) | Mitigation |
| --- | --- | --- |
| T-001.1 | Tampering: instructions hidden in uploaded data or documents steer the model into producing harmful SQL or code. | Uploaded content is marked as data; every output passes the SQL validator, the firewall and the sandbox regardless (REQ-001.12, .13, .20, .21, .38). |
| T-001.2 | Information disclosure: generated code sends the user's data to a third party. | Sandbox with no network and an isolated origin; firewall bans network APIs; a malicious-component test proves the sandbox alone holds (REQ-001.21). |
| T-001.3 | Elevation of privilege: generated code reaches the host page, its storage or other dashboards. | Isolated-origin sandbox, checked message protocol, components can only name approved queries (REQ-001.15, .21, .22). |
| T-001.4 | Information disclosure: a query uses the database's own file or network functions to read or send data. | SELECT-only validation, function blocklist, and external access disabled in the engine (REQ-001.13, .14). |
| T-001.5 | Tampering: someone publishes hostile code under our domain through a share link. | Only server-signed code can be stored; viewers run it in the same sandbox; the share page holds no secrets (REQ-001.23, .33, .34). |
| T-001.6 | Spoofing: the signing key leaks or signatures are forged. | Key held only in the host's secret store, compared in constant time, rotatable (rotation invalidates existing shares). |
| T-001.7 | Information disclosure: share links are guessed or enumerated. | 128-bit random ids, no listing, identical not-found responses, rate limiting (REQ-001.32, .35). |
| T-001.8 | Information disclosure: a shared data slice contains personal data, possibly about minors. | Explicit consent dialog with a no-personal-data-about-others confirmation, only the columns used, 10 MB cap, 7-day expiry, delete link (REQ-001.31 to .35). Residual risk accepted, see conflict 3. |
| T-001.9 | Information disclosure: personal data reaches model providers in prompts or screenshots. | Minimised payloads, raw rows opt-in, the visual check can be switched off, notice before upload (REQ-001.37, .40). See conflicts 1 and 2. |
| T-001.10 | Information disclosure: personal data in logs. | Allowlist logging, tested (REQ-001.39). |
| T-001.11 | Denial of service on the allowance: an anonymous visitor uses up the free model quota so nobody else can use the demo. | Token limits per request, per visitor per day and for the whole demo per day; a clean message when the provider's quota is gone (REQ-001.41, .42). |
| T-001.12 | Denial of service: a hostile document (oversized, deeply nested, decompression bomb) exhausts the parser. | Size, page and time limits; in-memory parsing with no external tools (REQ-001.5, .8). |
| T-001.13 | Denial of service: a runaway query or component freezes the browser. | Query timeout and row cap; render time limit (REQ-001.16, .25). |
| T-001.14 | Tampering: text inside a chart instructs the vision model. | Structured verdict only; any revision is firewalled again (REQ-001.28, .29). |
| T-001.15 | Information disclosure: provider API keys leak. | Keys exist only on the server, never in the browser or logs; secret scanning in CI. |
| T-001.16 | Tampering (supply chain): a compromised dependency, or a runtime script from a CDN. | Lockfiles and audits; the sandbox runtime ships React and ECharts from our own bundle, nothing fetched at run time. |

Accepted, not mitigated: with no accounts there is no way to attribute abuse to a person
(repudiation). The token limits bound the damage instead.

Privacy checklist (privacy-minors skill): minimise (met: column slices, minimised
prompts); pseudonymise (met: hashed rate-limit keys, no identities held); retention and
delete path for every field (met: table above); logging (met: REQ-001.39); guardian
consent for under-18s (cannot be verified; handled by the product owner's decision in
conflict 3).

## Telemetry
All of it content-free, as REQ-001.39 requires.
- Per generation: a random request id, provider and model, input and output token
  counts, validation outcomes, retries used for SQL and for code, whether it converged,
  critic verdict counts, and stage durations.
- Counters: shares created, viewed, deleted and expired; refusals by limit (per request,
  per visitor, shared pool, provider quota); document-parse refusals by reason.
- Daily tokens used against the shared pool.
- Candidate metric for `ops/bands.yaml`: the share of requests that fail to converge.
- No alerts; there is no on-call for a portfolio project.

## Conflicts flagged for the human
1. **Accurate filters need real values; privacy says send none.** A query like
   `status = 'Shipped'` is only right if the model has seen the value. ADR-0001 says
   sample values are opt-in. Decision taken, differing slightly from the ADR: by default
   send the distinct values of text columns that have 20 or fewer of them, skip any column
   that looks personal (names, emails, phone numbers, addresses, identifiers), and keep
   raw rows opt-in. If you would rather hold to the ADR strictly, accuracy on real data
   will drop.
2. **The layout critic sends a picture of the chart, including the numbers on it, to a
   model provider.** Decision taken: on by default, stated in the notice, with a switch to
   turn it off.
3. **Share links store data we cannot inspect, which may be personal and may be about
   under-18s.** The privacy skill requires guardian consent before storing minors' data,
   and an account-less app cannot check anyone's age. Decided by the product owner on
   2026-11-15: keep sharing the data, and require the user to confirm in the consent
   dialog that it contains no personal data about other people (REQ-001.31). The
   alternatives, sharing only code and queries or dropping sharing, were not taken. The
   residual risk is that a user ticks the statement untruthfully; the column slice, size
   cap, 7-day expiry and delete link limit the exposure.
4. **`evals/` means two things.** The playbook uses it for tests of the agent's own
   configuration; ADR-0001 used it for the Spider/BIRD harness. Decision taken: the
   product harness is `bench/`, and ADR-0001 gets a one-line amendment in the plan's PR.
5. **Rate limiting needs the client address; the rules say never log personal data.**
   Decision taken: a salted hash held in memory for at most a day, never written to logs
   or storage.
6. **Model usage has to fit free API tiers.** Decided by the product owner on 2026-11-15:
   model providers are used on their free tiers, so limits are counted in tokens, not
   money. In the demo: 100,000 combined tokens per request, 100,000 per visitor per day,
   and a shared daily pool for the whole demo whose size is set once the chosen
   provider's free quota is known (REQ-001.41). Benchmarks get their own daily allowance
   and resume across days (REQ-001.49), because one full run needs roughly 3 to 5 million
   tokens per provider and the intent's targets stay as accepted. A full run will
   therefore take several days.
7. **Scanned PDFs are refused.** Reading them needs OCR, which is a further model call
   per page. Decision taken: no OCR; the user is told why (REQ-001.8).
8. **CI will fail on the spec's own pull request.** The workflow runs `pnpm` commands
   that do not exist until the plan is implemented. Decision taken: accept red CI on the
   document-only PRs for the spec and plan.
9. **Free model tiers may come with weaker data terms.** Some providers reserve the right
   to use what is sent on a free tier to improve their services, which matters when
   visitors may upload personal data. Not checked for any specific provider yet. Decision
   taken: the notice names the provider in use and says plainly how it may use what it
   receives (REQ-001.40), and each provider's free-tier data terms are read before it is
   enabled in the plan. If no acceptable provider exists, this comes back to you.
10. **Free tiers and the quality targets pull against each other.** The published scores
   behind the intent's targets come from the strongest paid models. The models available
   on free tiers may score lower. Decision taken: keep the targets as accepted, report
   honestly against them, and revisit them after the first full run, as the intent
   already allows.

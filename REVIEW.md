# Review checklist
Used by you, the reviewer subagent and the CI AI review.
Rank every finding: critical / high / medium / low / nit.

1. Correctness: does the diff do what spec.md and plan.md say? Anything extra?
2. Tests: every REQ in scope has a test; tests assert behaviour, not implementation.
3. Security: input validation, authz on every endpoint, no secrets, no injection.
4. Privacy: no personal data in logs; minors' data minimised and pseudonymised.
5. Reliability: errors handled, timeouts, pagination limits, idempotent migrations.
6. Observability: the telemetry named in the spec is emitted.
7. Docs: ADR / threat model / README updated if behaviour changed.

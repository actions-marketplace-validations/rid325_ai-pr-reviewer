# Changelog

## 2.0.0

- Split deterministic core, GitHub transport, Gemini adapter, and orchestration code.
- Added paginated changed-file retrieval and explicit HTTP timeouts.
- Added schema-constrained Gemini responses with bounded retry behavior.
- Disabled nested SDK retries and added a per-request deadline so transient outages cannot consume the whole job timeout.
- Validate filenames and right-side added line numbers before posting.
- Added diff, total-run, and comment budgets plus skip reporting.
- Added idempotent summary comments and a 422 posting fallback.
- Added dry-run mode, outputs, tests, CI, and non-root Python 3.12 container.
- Documented prompt-injection, fork-secret, and least-privilege constraints.

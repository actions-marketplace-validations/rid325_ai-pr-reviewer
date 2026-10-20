# Changelog

## 2.0.0

- Split deterministic core, GitHub transport, Gemini adapter, and orchestration code.
- Added paginated changed-file retrieval and explicit HTTP timeouts.
- Added schema-constrained Gemini responses with bounded retry behavior.
- Disabled nested SDK retries and added a per-request deadline so transient outages cannot consume the whole job timeout.
- Added an ordered stable-model fallback when the preferred Gemini endpoint is unavailable.
- Defaulted to the stable high-throughput Flash-Lite family after live 3.8 capacity testing.
- Added bounded inter-chunk pacing for constrained Gemini API tiers.
- Added a privilege-dropping container shim so non-root ReviewBot can write GitHub Action outputs safely.
- Validate filenames and right-side added line numbers before posting.
- Added diff, total-run, and comment budgets plus skip reporting.
- Added idempotent summary comments and a 422 posting fallback.
- Added dry-run mode, outputs, tests, CI, and non-root Python 3.12 container.
- Documented prompt-injection, fork-secret, and least-privilege constraints.

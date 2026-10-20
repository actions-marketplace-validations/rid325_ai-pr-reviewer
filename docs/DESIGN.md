# ReviewBot design

## Goals

ReviewBot provides bounded, explainable first-pass feedback on pull-request changes. It optimizes for high-signal findings and safe failure, not maximum comment volume.

## Trust boundaries

There are three untrusted inputs: the pull-request diff, the model response, and remote API responses. Diff content is marked as data in the prompt. Model output must satisfy a JSON schema and then passes deterministic application validation. HTTP calls have timeouts and non-success responses fail the Action, except for the documented inline-comment 422 fallback.

## Decisions

### Comment only on added lines

GitHub's review API accepts right-side line comments only at valid diff positions. The parser builds the allowed line set from each unified-diff hunk. This also prevents a model from inventing a filename or line number. The trade-off is that deletion-only findings can appear only in a general summary, which v2 does not yet generate.

### Bound cost and latency

Files are sorted by changed-line count, individual requests are capped by `max_diff_lines`, and the run has a total budget of four times that value. A maximum comment count prevents noisy reviews. Every skipped file and reason appears in the PR summary.

At most four chunks are generated. A 30-second default interval between chunk requests trades a small amount of latency for compatibility with constrained Gemini API tiers; users with higher quotas can set it to zero.

### Prefer one review and one summary

Validated findings are submitted in a single GitHub review. A 422 response—usually an invalidated diff position after a force-push—falls back to a general PR comment so useful feedback is not lost. The run summary carries a hidden marker and is updated rather than duplicated.

### Fail visibly

Authentication, quota, model, schema, and GitHub posting errors produce a non-zero exit. Silent success is worse than a failed check because it makes maintainers believe a review occurred.

Gemini requests have a 60-second deadline. SDK-level retries are disabled and the adapter owns the retry policy, preventing nested retries from turning a temporary 503 into an unbounded job. Models are tried in configured order; the default favors the stable high-throughput Gemini 3.5 Flash-Lite and falls back once to Gemini 3.1 Flash-Lite. Users can select Gemini 3.8 Flash when its additional reasoning quality is worth higher latency and current capacity allows it.

The container starts only long enough as root to change ownership of files under GitHub's fixed `/github/file_commands` mount. It rejects any other path and immediately drops to UID/GID 10001 before importing or running the reviewer.

## Known extensions

- Fetch limited surrounding source context after validating paths.
- Add metrics from a hand-labeled PR corpus instead of claiming an unmeasured accuracy rate.
- Support provider adapters selected through configuration.
- Add a check-run annotation mode for fork pull requests without sharing a model key.

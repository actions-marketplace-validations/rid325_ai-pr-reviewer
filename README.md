![ReviewBot demo](assets/demo.gif)

# ReviewBot

A defensive GitHub Action that uses Gemini to review pull-request diffs and leaves comments only after mapping every finding back to a real added line.

[![CI](https://github.com/rid325/ai-pr-reviewer/actions/workflows/ci.yml/badge.svg)](https://github.com/rid325/ai-pr-reviewer/actions/workflows/ci.yml)
[![Review PRs](https://github.com/rid325/ai-pr-reviewer/actions/workflows/review.yml/badge.svg)](https://github.com/rid325/ai-pr-reviewer/actions/workflows/review.yml)
[![License: MIT](https://img.shields.io/github/license/rid325/ai-pr-reviewer)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)

## Why this is more than an API wrapper

LLM output is never trusted directly. ReviewBot paginates GitHub's changed-file API, filters and budgets the diff, requests schema-constrained JSON, and then rejects hallucinated filenames, non-added line numbers, invalid severity values, oversized comments, and duplicates before posting. A failed Gemini or GitHub request fails the Action instead of reporting a false success.

It is designed to find concrete correctness, security, error-handling, and material performance problems. It deliberately avoids style-only feedback.

## Setup

1. Create a Gemini API key and save it as the repository secret `GEMINI_API_KEY`.
2. Add `.github/workflows/reviewbot.yml`:

```yaml
name: ReviewBot
on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]

jobs:
  review:
    if: github.event.pull_request.draft == false
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
      - uses: rid325/ai-pr-reviewer@v2
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          gemini_api_key: ${{ secrets.GEMINI_API_KEY }}
```

Pin an immutable release such as `@v2.0.0` instead of `@v2` when reproducibility matters more than automatic compatible fixes.

## Configuration

| Input | Required | Default | Purpose |
|---|---:|---|---|
| `github_token` | yes | — | Token with `pull-requests: write` |
| `gemini_api_key` | yes | — | Gemini API credential |
| `ignore_patterns` | no | `*.lock,package-lock.json,*.generated.*` | Comma-separated `fnmatch` patterns |
| `max_diff_lines` | no | `500` | Changed lines per model request; minimum 25 |
| `max_comments` | no | `20` | Validated findings posted per run; maximum 50 |
| `model` | no | `gemini-3.8-flash` | Gemini model ID |
| `dry_run` | no | `false` | Analyze and log without posting |

The Action outputs `issues_found`, `files_reviewed`, and `files_skipped` for downstream steps.

## Pipeline

```text
pull_request event
      │
      ▼
paginated GitHub file fetch
      │
      ▼
ignore rules → missing-patch detection → line budget → chunking
      │
      ▼
Gemini structured JSON (bounded retries)
      │
      ▼
schema + filename + added-line + size + duplicate validation
      │
      ├── valid findings → inline review (general-comment fallback on GitHub 422)
      └── run metadata  → one idempotently updated summary comment
```

See [the design notes](docs/DESIGN.md) for trade-offs and [the security policy](SECURITY.md) for the trust model.

## Security and fork behavior

- Diff text is delimited as untrusted data and prompt instructions inside it are ignored.
- ReviewBot uses `pull_request`, never `pull_request_target`; untrusted fork code therefore does not run with repository secrets.
- GitHub withholds Actions secrets from fork pull requests. The example workflow should skip those runs or let a maintainer run ReviewBot after inspecting the branch.
- Grant only `contents: read` and `pull-requests: write`. Never store a personal access token when `GITHUB_TOKEN` is sufficient.

## Honest limitations

- ReviewBot sees a diff, not full runtime behavior or complete repository context. Findings are advisory and require human judgment.
- GitHub can omit `patch` for binary or very large files; these are named in the summary and skipped.
- The total review budget is four times `max_diff_lines`; files beyond it are reported as skipped. This bounds cost and latency.
- Findings are limited to added right-side lines, so a real issue caused only by deleted or unchanged code cannot receive an inline comment.
- Model availability, quota, price, and behavior are controlled by Google. Override `model` if the default is unavailable to your account.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest -q
docker build -t reviewbot .
```

See [CONTRIBUTING.md](CONTRIBUTING.md). Licensed under [MIT](LICENSE).

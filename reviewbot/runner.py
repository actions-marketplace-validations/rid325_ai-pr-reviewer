"""GitHub Action entrypoint."""
from __future__ import annotations

import json
import os
from pathlib import Path

from reviewbot.core import Finding, prepare_diff, validate_findings
from reviewbot.gemini_client import GeminiReviewer
from reviewbot.github_client import GitHubClient


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"required environment variable {name} is missing")
    return value


def _boolean(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, str(default)).lower()
    if raw not in {"true", "false", "1", "0", "yes", "no"}:
        raise ValueError(f"{name} must be a boolean")
    return raw in {"true", "1", "yes"}


def _write_output(name: str, value: object) -> None:
    path = os.getenv("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as output:
            output.write(f"{name}={value}\n")


def _summary(findings: list[Finding], prepared, rejected: list[str], mode: str) -> str:
    counts = {severity: sum(item.severity == severity for item in findings) for severity in ("high", "medium", "low")}
    body = ["### 🤖 ReviewBot summary", ""]
    if findings:
        body.append(
            f"Reviewed **{len(prepared.reviewed_files)} files / {prepared.diff_lines} changed lines** and "
            f"accepted **{len(findings)} validated findings** "
            f"({counts['high']} high, {counts['medium']} medium, {counts['low']} low)."
        )
    else:
        body.append(
            f"Reviewed **{len(prepared.reviewed_files)} files / {prepared.diff_lines} changed lines**; "
            "no validated issues were found."
        )
    if prepared.skipped_files:
        body.extend(["", "**Skipped files**"])
        body.extend(f"- `{name}` — {reason}" for name, reason in prepared.skipped_files)
    if rejected:
        body.extend(["", f"Discarded {len(rejected)} model finding(s) that did not map to an added diff line or valid schema."])
    body.extend(["", f"Posting mode: `{mode}`. Model output is advisory; verify findings before changing code."])
    return "\n".join(body)


def run() -> int:
    repository = _required("GITHUB_REPOSITORY")
    token = _required("INPUT_GITHUB_TOKEN")
    api_key = _required("INPUT_GEMINI_API_KEY")
    event_path = Path(_required("GITHUB_EVENT_PATH"))
    event = json.loads(event_path.read_text(encoding="utf-8"))
    pull_request = event.get("pull_request")
    if not isinstance(pull_request, dict) or not pull_request.get("number"):
        raise ValueError("ReviewBot only supports pull_request events")
    pr_number = int(pull_request["number"])
    ignore_patterns = [
        pattern.strip() for pattern in os.getenv("INPUT_IGNORE_PATTERNS", "").split(",")
        if pattern.strip()
    ]
    max_diff_lines = int(os.getenv("INPUT_MAX_DIFF_LINES", "500"))
    max_comments = int(os.getenv("INPUT_MAX_COMMENTS", "20"))
    if not 1 <= max_comments <= 50:
        raise ValueError("INPUT_MAX_COMMENTS must be between 1 and 50")
    dry_run = _boolean("INPUT_DRY_RUN")
    model = os.getenv("INPUT_MODEL", "gemini-3.8-flash").strip()
    if not model:
        raise ValueError("INPUT_MODEL must not be empty")

    github = GitHubClient(repository, token)
    prepared = prepare_diff(github.get_pull_files(pr_number), ignore_patterns, max_diff_lines)
    all_findings: list[Finding] = []
    rejected: list[str] = []
    if prepared.chunks:
        reviewer = GeminiReviewer(api_key, model)
        for index, chunk in enumerate(prepared.chunks, start=1):
            print(f"Reviewing chunk {index}/{len(prepared.chunks)}...", flush=True)
            findings, invalid = validate_findings(
                reviewer.review(chunk), prepared.commentable_lines, max_comments - len(all_findings),
            )
            all_findings.extend(findings)
            rejected.extend(invalid)
            if len(all_findings) >= max_comments:
                break

    mode = "dry-run" if dry_run else "summary-only"
    if not dry_run and all_findings:
        mode = github.post_review(pr_number, all_findings)
    if not dry_run:
        github.upsert_summary(pr_number, _summary(all_findings, prepared, rejected, mode))

    _write_output("issues_found", len(all_findings))
    _write_output("files_reviewed", len(prepared.reviewed_files))
    _write_output("files_skipped", len(prepared.skipped_files))
    print(_summary(all_findings, prepared, rejected, mode))
    return 0


def main() -> None:
    try:
        raise SystemExit(run())
    except Exception as error:
        print(f"ReviewBot failed: {error}", flush=True)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()

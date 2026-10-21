"""Pure diff preparation and finding validation logic."""
from __future__ import annotations

from dataclasses import dataclass
import fnmatch
import re
from typing import Iterable


ALLOWED_SEVERITIES = {"low", "medium", "high"}
HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


@dataclass(frozen=True)
class ChangedFile:
    filename: str
    patch: str
    changes: int = 0


@dataclass(frozen=True)
class PreparedDiff:
    chunks: list[str]
    commentable_lines: dict[str, set[int]]
    reviewed_files: list[str]
    skipped_files: list[tuple[str, str]]
    diff_lines: int


@dataclass(frozen=True)
class Finding:
    file: str
    line: int
    severity: str
    comment: str
    suggestion: str | None = None


def count_diff_lines(patch: str) -> int:
    changed = 0
    in_hunk = False
    for line in patch.splitlines():
        if HUNK_HEADER.match(line):
            in_hunk = True
            continue
        if in_hunk and (line.startswith("+") or line.startswith("-")):
            changed += 1
    return changed


def added_lines(patch: str) -> set[int]:
    """Return right-side line numbers that GitHub accepts for inline comments."""
    result: set[int] = set()
    new_line: int | None = None
    for line in patch.splitlines():
        match = HUNK_HEADER.match(line)
        if match:
            new_line = int(match.group(1))
            continue
        if new_line is None or line.startswith("\\ No newline"):
            continue
        if line.startswith("+"):
            result.add(new_line)
            new_line += 1
        elif line.startswith("-"):
            continue
        else:
            new_line += 1
    return result


def _split_large_patch(filename: str, patch: str, max_diff_lines: int) -> list[str]:
    chunks: list[str] = []
    part: list[str] = []
    changed = 0
    new_line: int | None = None
    in_hunk = False
    for line in patch.splitlines():
        header = HUNK_HEADER.match(line)
        if header:
            in_hunk = True
            new_line = int(header.group(1))
        is_changed = (
            in_hunk
            and not header
            and (line.startswith("+") or line.startswith("-"))
        )
        if part and is_changed and changed >= max_diff_lines:
            chunks.append(f"\n=== {filename} ===\n" + "\n".join(part))
            # A synthetic continuation header preserves right-side line context
            # when a single hunk is larger than the request budget.
            part = [f"@@ continuation +{new_line or 1} @@"]
            changed = 0
        part.append(line)
        changed += int(is_changed)
        if new_line is not None and not line.startswith("-") and not header and not line.startswith("\\ No newline"):
            new_line += 1
    if part:
        chunks.append(f"\n=== {filename} ===\n" + "\n".join(part))
    return chunks


def prepare_diff(
    raw_files: Iterable[dict],
    ignore_patterns: list[str],
    max_diff_lines: int,
    max_total_lines: int | None = None,
) -> PreparedDiff:
    if max_diff_lines < 25:
        raise ValueError("max_diff_lines must be at least 25")
    max_total_lines = max_total_lines or 4 * max_diff_lines
    files: list[ChangedFile] = []
    skipped: list[tuple[str, str]] = []
    for item in raw_files:
        filename = str(item.get("filename", ""))
        if not filename:
            continue
        if any(fnmatch.fnmatch(filename, pattern) for pattern in ignore_patterns):
            skipped.append((filename, "ignored by pattern"))
            continue
        patch = item.get("patch")
        if not patch:
            skipped.append((filename, "GitHub did not return a patch"))
            continue
        files.append(ChangedFile(filename, str(patch), int(item.get("changes", 0))))

    files.sort(key=lambda item: item.changes or count_diff_lines(item.patch), reverse=True)
    chunks: list[str] = []
    current: list[str] = []
    current_lines = total_lines = 0
    commentable: dict[str, set[int]] = {}
    reviewed: list[str] = []

    for item in files:
        line_count = count_diff_lines(item.patch)
        if total_lines + line_count > max_total_lines:
            skipped.append((item.filename, f"total review budget exceeded ({max_total_lines} lines)"))
            continue
        total_lines += line_count
        reviewed.append(item.filename)
        commentable[item.filename] = added_lines(item.patch)
        if line_count > max_diff_lines:
            if current:
                chunks.append("".join(current))
                current, current_lines = [], 0
            chunks.extend(_split_large_patch(item.filename, item.patch, max_diff_lines))
            continue
        file_diff = f"\n=== {item.filename} ===\n{item.patch}"
        if current and current_lines + line_count > max_diff_lines:
            chunks.append("".join(current))
            current, current_lines = [file_diff], line_count
        else:
            current.append(file_diff)
            current_lines += line_count
    if current:
        chunks.append("".join(current))

    return PreparedDiff(chunks, commentable, reviewed, skipped, total_lines)


def validate_findings(
    payload: object,
    commentable_lines: dict[str, set[int]],
    max_comments: int,
) -> tuple[list[Finding], list[str]]:
    """Accept only bounded findings attached to actual added right-side lines."""
    if max_comments <= 0:
        return [], []
    if isinstance(payload, dict):
        payload = payload.get("findings")
    if not isinstance(payload, list):
        raise ValueError("model response must contain a findings array")
    accepted: list[Finding] = []
    rejected: list[str] = []
    seen: set[tuple[str, int, str]] = set()
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            rejected.append(f"finding {index}: not an object")
            continue
        filename = item.get("file")
        comment = item.get("comment")
        severity = str(item.get("severity", "")).lower()
        try:
            line = int(item.get("line"))
        except (TypeError, ValueError):
            rejected.append(f"finding {index}: invalid line")
            continue
        if filename not in commentable_lines:
            rejected.append(f"finding {index}: file was not reviewed")
            continue
        if line not in commentable_lines[filename]:
            rejected.append(f"finding {index}: line is not an added diff line")
            continue
        if severity not in ALLOWED_SEVERITIES:
            rejected.append(f"finding {index}: invalid severity")
            continue
        if not isinstance(comment, str) or not comment.strip() or len(comment) > 1200:
            rejected.append(f"finding {index}: invalid comment")
            continue
        suggestion = item.get("suggestion")
        if suggestion is not None and (not isinstance(suggestion, str) or len(suggestion) > 4000):
            rejected.append(f"finding {index}: invalid suggestion")
            continue
        key = (filename, line, comment.strip())
        if key in seen:
            continue
        seen.add(key)
        accepted.append(Finding(filename, line, severity, comment.strip(), suggestion.strip() if suggestion else None))
        if len(accepted) >= max_comments:
            break
    return accepted, rejected

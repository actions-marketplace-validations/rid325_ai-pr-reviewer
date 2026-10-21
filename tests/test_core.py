import pytest

from reviewbot.core import count_diff_lines, added_lines, prepare_diff, validate_findings


PATCH = """@@ -1,3 +1,4 @@
 keep
-old
+new
+extra
 tail
"""


def test_counts_and_maps_only_added_lines():
    assert count_diff_lines(PATCH) == 3
    assert added_lines(PATCH) == {2, 3}


def test_removed_sql_comment_does_not_shift_added_line():
    patch = """@@ -1,3 +1,3 @@
 context
--- old sql comment
+new line
 context2
"""
    assert added_lines(patch) == {2}
    assert count_diff_lines(patch) == 2


def test_added_increment_expression_is_counted_and_commentable():
    patch = """@@ -1 +1,2 @@
 context
+++i;
"""
    assert count_diff_lines(patch) == 1
    assert added_lines(patch) == {2}


def test_removed_markdown_rule_does_not_shift_later_line():
    patch = """@@ -1,3 +1,3 @@
 context
----
+replacement
 tail
"""
    assert added_lines(patch) == {2}
    assert count_diff_lines(patch) == 2


def test_large_hunk_with_sql_comment_keeps_continuation_line_number():
    lines = [
        "@@ -1,2 +1,27 @@",
        " context",
        "--- sql comment",
        "+replacement",
        *[f"+added {index}" for index in range(25)],
    ]
    prepared = prepare_diff(
        [{"filename": "large.sql", "patch": "\n".join(lines), "changes": 27}],
        [],
        25,
    )
    assert len(prepared.chunks) == 2
    assert "@@ continuation +26 @@" in prepared.chunks[1]
    assert prepared.commentable_lines["large.sql"] == set(range(2, 28))


def test_prepare_diff_filters_missing_and_ignored_files():
    prepared = prepare_diff(
        [
            {"filename": "app.py", "patch": PATCH, "changes": 3},
            {"filename": "package-lock.json", "patch": PATCH, "changes": 3},
            {"filename": "image.png", "changes": 1},
        ],
        ["*.lock", "package-lock.json"],
        25,
    )
    assert prepared.reviewed_files == ["app.py"]
    assert prepared.commentable_lines == {"app.py": {2, 3}}
    assert prepared.diff_lines == 3
    assert prepared.skipped_files == [
        ("package-lock.json", "ignored by pattern"),
        ("image.png", "GitHub did not return a patch"),
    ]


def test_prepare_diff_enforces_total_budget():
    raw = [
        {"filename": f"file{index}.py", "patch": PATCH, "changes": 3}
        for index in range(3)
    ]
    prepared = prepare_diff(raw, [], 25, max_total_lines=6)
    assert len(prepared.reviewed_files) == 2
    assert prepared.skipped_files[0][1].startswith("total review budget exceeded")


def test_prepare_diff_rejects_tiny_chunk_limit():
    with pytest.raises(ValueError, match="at least 25"):
        prepare_diff([], [], 10)


def test_large_hunk_chunks_keep_right_side_line_context():
    lines = ["@@ -1,30 +1,30 @@"] + [f"+line {index}" for index in range(30)]
    prepared = prepare_diff(
        [{"filename": "large.py", "patch": "\n".join(lines), "changes": 30}],
        [],
        25,
    )
    assert len(prepared.chunks) == 2
    assert "@@ continuation +26 @@" in prepared.chunks[1]
    assert all(count_diff_lines(chunk) <= 25 for chunk in prepared.chunks)


def test_validation_rejects_hallucinated_locations_and_bad_schema():
    payload = {
        "findings": [
            {"file": "app.py", "line": 2, "severity": "HIGH", "comment": "Real bug"},
            {"file": "other.py", "line": 2, "severity": "high", "comment": "Wrong file"},
            {"file": "app.py", "line": 99, "severity": "high", "comment": "Wrong line"},
            {"file": "app.py", "line": 3, "severity": "urgent", "comment": "Bad severity"},
            {"file": "app.py", "line": "nope", "severity": "low", "comment": "Bad line"},
        ]
    }
    findings, rejected = validate_findings(payload, {"app.py": {2, 3}}, 20)
    assert [(item.file, item.line, item.severity) for item in findings] == [("app.py", 2, "high")]
    assert len(rejected) == 4


def test_validation_deduplicates_and_caps_findings():
    repeated = {"file": "app.py", "line": 2, "severity": "low", "comment": "Same"}
    payload = {"findings": [repeated, repeated, {**repeated, "line": 3, "comment": "Second"}]}
    findings, _ = validate_findings(payload, {"app.py": {2, 3}}, 1)
    assert len(findings) == 1
    assert validate_findings(payload, {"app.py": {2, 3}}, 0) == ([], [])


def test_validation_requires_findings_array():
    with pytest.raises(ValueError, match="findings array"):
        validate_findings({}, {}, 10)

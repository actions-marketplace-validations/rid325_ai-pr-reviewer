import json

import pytest

from reviewbot import runner


class GitHub:
    instances = []

    def __init__(self, repository, token):
        self.repository = repository
        self.token = token
        self.reviews = []
        self.summaries = []
        self.__class__.instances.append(self)

    def get_pull_files(self, number):
        return [{"filename": "app.py", "patch": "@@ -1 +1 @@\n-old\n+new", "changes": 2}]

    def post_review(self, number, findings):
        self.reviews.append((number, findings))
        return "inline"

    def upsert_summary(self, number, body):
        self.summaries.append((number, body))


class Reviewer:
    def __init__(self, api_key, model):
        self.api_key = api_key
        self.models = model

    def review(self, diff):
        return {"findings": [{"file": "app.py", "line": 1, "severity": "high", "comment": "Bug"}]}


def set_environment(monkeypatch, tmp_path):
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"pull_request": {"number": 9}}), encoding="utf-8")
    values = {
        "GITHUB_REPOSITORY": "owner/repo",
        "INPUT_GITHUB_TOKEN": "token",
        "INPUT_GEMINI_API_KEY": "key",
        "GITHUB_EVENT_PATH": str(event),
        "INPUT_MAX_DIFF_LINES": "25",
        "INPUT_MAX_COMMENTS": "5",
        "INPUT_REQUEST_INTERVAL_SECONDS": "0",
        "INPUT_MODEL": "test-model",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def test_run_posts_validated_review_and_summary(monkeypatch, tmp_path):
    set_environment(monkeypatch, tmp_path)
    GitHub.instances.clear()
    monkeypatch.setattr(runner, "GitHubClient", GitHub)
    monkeypatch.setattr(runner, "GeminiReviewer", Reviewer)
    assert runner.run() == 0
    api = GitHub.instances[0]
    assert len(api.reviews[0][1]) == 1
    assert "Posting mode: `inline`" in api.summaries[0][1]


def test_dry_run_does_not_post(monkeypatch, tmp_path):
    set_environment(monkeypatch, tmp_path)
    monkeypatch.setenv("INPUT_DRY_RUN", "true")
    GitHub.instances.clear()
    monkeypatch.setattr(runner, "GitHubClient", GitHub)
    monkeypatch.setattr(runner, "GeminiReviewer", Reviewer)
    assert runner.run() == 0
    assert not GitHub.instances[0].reviews
    assert not GitHub.instances[0].summaries


def test_missing_pr_event_is_rejected(monkeypatch, tmp_path):
    set_environment(monkeypatch, tmp_path)
    event = tmp_path / "bad-event.json"
    event.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))
    with pytest.raises(ValueError, match="pull_request events"):
        runner.run()

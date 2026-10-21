import requests

from reviewbot.core import Finding
from reviewbot.github_client import GitHubClient, SUMMARY_MARKER


class Response:
    def __init__(self, data=None, status=200, url="https://api.github.test/item"):
        self.data = data
        self.status_code = status
        self.url = url

    def json(self):
        return self.data

    def raise_for_status(self):
        if self.status_code >= 400:
            error = requests.HTTPError(f"HTTP {self.status_code}")
            error.response = self
            raise error


class Session:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.headers = {}

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.responses.pop(0)


def client(responses):
    return GitHubClient("owner/repo", "token", session=Session(responses))


def test_pull_files_are_paginated():
    api = client([Response([{"filename": f"f{i}"} for i in range(100)]), Response([{"filename": "last"}])])
    assert len(api.get_pull_files(7)) == 101
    assert api.session.calls[1][2]["params"]["page"] == 2


def test_inline_review_posts_suggestion():
    api = client([Response({})])
    mode = api.post_review(7, [Finding("app.py", 4, "high", "Bug", "fixed()")])
    assert mode == "inline"
    payload = api.session.calls[0][2]["json"]
    assert "```suggestion\nfixed()\n```" in payload["comments"][0]["body"]


def test_422_uses_general_comment_fallback():
    api = client([Response({}, 422), Response({})])
    mode = api.post_review(7, [Finding("app.py", 4, "high", "Bug", "fixed()")])
    assert mode == "fallback"
    assert api.session.calls[1][0] == "POST"
    assert "Suggested replacement" in api.session.calls[1][2]["json"]["body"]


def test_non_422_posting_failure_is_not_swallowed():
    api = client([Response({}, 500)])
    try:
        api.post_review(7, [Finding("app.py", 4, "high", "Bug")])
        assert False, "expected HTTPError"
    except requests.HTTPError:
        pass


def test_summary_updates_existing_bot_comment():
    api = client([Response([{"body": SUMMARY_MARKER, "url": "https://api.github.test/comment/1"}]), Response({})])
    api.upsert_summary(7, "New summary")
    assert api.session.calls[1][0] == "PATCH"
    assert api.session.calls[1][2]["json"]["body"].startswith(SUMMARY_MARKER)

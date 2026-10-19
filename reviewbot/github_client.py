"""Small GitHub REST client with explicit failure handling."""
from __future__ import annotations

import requests

from reviewbot.core import Finding


SUMMARY_MARKER = "<!-- reviewbot-summary -->"


class GitHubClient:
    def __init__(self, repository: str, token: str, timeout: int = 20, session=None):
        self.repository = repository
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "reviewbot-action/2.0",
        })
        self.base = f"https://api.github.com/repos/{repository}"

    def _request(self, method: str, url: str, **kwargs):
        response = self.session.request(method, url, timeout=self.timeout, **kwargs)
        response.raise_for_status()
        return response

    def get_pull_files(self, pr_number: int) -> list[dict]:
        files: list[dict] = []
        page = 1
        while True:
            response = self._request(
                "GET", f"{self.base}/pulls/{pr_number}/files",
                params={"per_page": 100, "page": page},
            )
            batch = response.json()
            if not isinstance(batch, list):
                raise ValueError("GitHub files response was not a list")
            files.extend(batch)
            if len(batch) < 100:
                return files
            page += 1

    def post_review(self, pr_number: int, findings: list[Finding]) -> str:
        comments = []
        for finding in findings:
            body = f"**[{finding.severity.upper()}]** {finding.comment}"
            if finding.suggestion:
                body += f"\n\n```suggestion\n{finding.suggestion}\n```"
            comments.append({
                "path": finding.file, "line": finding.line,
                "side": "RIGHT", "body": body,
            })
        try:
            self._request(
                "POST", f"{self.base}/pulls/{pr_number}/reviews",
                json={"event": "COMMENT", "comments": comments},
            )
            return "inline"
        except requests.HTTPError as error:
            if error.response is None or error.response.status_code != 422:
                raise
            body = "### ReviewBot findings\n\n" + "\n\n---\n\n".join(
                f"**{item.file}:{item.line} · {item.severity.upper()}**\n\n{item.comment}"
                + (f"\n\nSuggested replacement:\n```\n{item.suggestion}\n```" if item.suggestion else "")
                for item in findings
            )
            self._request(
                "POST", f"{self.base}/issues/{pr_number}/comments", json={"body": body},
            )
            return "fallback"

    def upsert_summary(self, pr_number: int, body: str) -> None:
        body = f"{SUMMARY_MARKER}\n{body}"
        response = self._request(
            "GET", f"{self.base}/issues/{pr_number}/comments", params={"per_page": 100},
        )
        for comment in response.json():
            if SUMMARY_MARKER in comment.get("body", ""):
                self._request("PATCH", comment["url"], json={"body": body})
                return
        self._request("POST", f"{self.base}/issues/{pr_number}/comments", json={"body": body})

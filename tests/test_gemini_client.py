import pytest

from reviewbot.gemini_client import GeminiReviewer


class Models:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return type("ModelResponse", (), {"text": outcome})()


class Client:
    def __init__(self, outcomes):
        self.models = Models(outcomes)


def test_structured_response_and_untrusted_diff_boundary():
    fake = Client(['{"findings": []}'])
    result = GeminiReviewer("key", "model", client=fake).review("+ risky()")
    assert result == {"findings": []}
    call = fake.models.calls[0]
    assert "<UNTRUSTED_DIFF>" in call["contents"]
    assert call["config"].response_mime_type == "application/json"


def test_retry_then_success(monkeypatch):
    monkeypatch.setattr("reviewbot.gemini_client.time.sleep", lambda _: None)
    fake = Client([RuntimeError("temporary"), '{"findings": []}'])
    assert GeminiReviewer("key", "model", attempts=2, client=fake).review("diff") == {"findings": []}
    assert len(fake.models.calls) == 2


def test_exhausted_retries_fail_the_action(monkeypatch):
    monkeypatch.setattr("reviewbot.gemini_client.time.sleep", lambda _: None)
    fake = Client([RuntimeError("bad"), RuntimeError("bad")])
    with pytest.raises(RuntimeError, match="after 2 attempts"):
        GeminiReviewer("key", "model", attempts=2, client=fake).review("diff")


def test_falls_back_to_second_model(monkeypatch):
    monkeypatch.setattr("reviewbot.gemini_client.time.sleep", lambda _: None)
    fake = Client([RuntimeError("capacity"), '{"findings": []}'])
    result = GeminiReviewer("key", ["preferred", "fallback"], client=fake).review("diff")
    assert result == {"findings": []}
    assert [call["model"] for call in fake.models.calls] == ["preferred", "fallback"]


def test_disables_nested_sdk_retries_and_sets_deadline(monkeypatch):
    captured = {}

    def build_client(**kwargs):
        captured.update(kwargs)
        return Client(['{"findings": []}'])

    monkeypatch.setattr("reviewbot.gemini_client.genai.Client", build_client)
    GeminiReviewer("key", "model", request_timeout_ms=12_345)
    options = captured["http_options"]
    assert options.timeout == 12_345
    assert options.retry_options.attempts == 1

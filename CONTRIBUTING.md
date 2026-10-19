# Contributing to ReviewBot

Keep changes focused and include a regression test for behavior changes.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest -q
python -m compileall -q reviewbot scripts
```

The CI workflow runs those checks and builds the Action container.

## Safe integration testing

Create a draft pull request in a test repository. Set the normal Action environment variables and enable `INPUT_DRY_RUN=true` while iterating; there is no need to edit out posting code. A minimal event fixture is:

```json
{"pull_request": {"number": 42}}
```

Then run:

```bash
export GITHUB_REPOSITORY="owner/repo"
export GITHUB_EVENT_PATH="$PWD/test-event.json"
export INPUT_GITHUB_TOKEN="..."
export INPUT_GEMINI_API_KEY="..."
export INPUT_DRY_RUN="true"
python -m reviewbot.runner
```

Do not commit keys or event payloads containing private data.

## Architecture boundaries

- `reviewbot/core.py` contains deterministic diff and validation logic.
- `reviewbot/github_client.py` owns GitHub HTTP behavior.
- `reviewbot/gemini_client.py` owns model prompting and structured output.
- `reviewbot/runner.py` coordinates one Action run.

Keep provider-specific behavior behind an adapter so the validation and posting pipeline stays provider-independent. See [docs/DESIGN.md](docs/DESIGN.md).

Use Conventional Commit prefixes such as `feat:`, `fix:`, `test:`, `docs:`, and `refactor:`. Issue reports should include the Action run link, approximate diff size, relevant skipped-file summary, observed result, and expected result—with secrets removed.

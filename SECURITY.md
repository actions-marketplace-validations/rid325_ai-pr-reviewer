# Security policy

## Reporting

Do not open a public issue for a vulnerability that could expose credentials or affect users. Email the repository owner through the private contact listed on their GitHub profile with reproduction steps and impact. Do not include real API keys.

## Operational guidance

- Use the repository-scoped `GITHUB_TOKEN`, not a personal access token.
- Grant `contents: read` and `pull-requests: write` only.
- Store the Gemini key as an Actions secret and rotate it if it appears in logs or a commit.
- Use the `pull_request` event. Do not change the workflow to `pull_request_target` and then check out or execute fork code.
- Treat every model finding as advisory.

## Supported version

Security fixes are made on the current major version (`v2`). Pin the latest immutable `v2.x.y` tag if your workflow requires reproducible dependencies.

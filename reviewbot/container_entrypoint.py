"""Prepare GitHub's mounted command files, then drop container privileges."""
from __future__ import annotations

import os
from pathlib import Path


RUN_UID = 10001
RUN_GID = 10001
FILE_COMMAND_ROOT = Path("/github/file_commands")
FILE_COMMAND_ENV = ("GITHUB_OUTPUT", "GITHUB_STEP_SUMMARY", "GITHUB_ENV", "GITHUB_PATH")


def prepare_runtime() -> None:
    if os.geteuid() != 0:
        return
    for name in FILE_COMMAND_ENV:
        raw_path = os.getenv(name)
        if not raw_path:
            continue
        path = Path(raw_path).resolve()
        if FILE_COMMAND_ROOT not in path.parents or not path.exists():
            continue
        os.chown(path, RUN_UID, RUN_GID)
    os.setgid(RUN_GID)
    os.setuid(RUN_UID)


def main() -> None:
    prepare_runtime()
    from reviewbot.runner import main as run_reviewbot

    run_reviewbot()


if __name__ == "__main__":
    main()

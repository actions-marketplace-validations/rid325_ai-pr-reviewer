"""Compatibility entrypoint; the Docker Action runs ``python -m reviewbot.runner``."""
from reviewbot.runner import main


if __name__ == "__main__":
    main()

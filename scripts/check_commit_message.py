"""Require a Conventional Commit subject and a DCO Signed-off-by trailer."""

import argparse
import re
import subprocess
import sys
from pathlib import Path

SUBJECT = re.compile(r"[a-z][a-z0-9-]*(?:\([^()\r\n]+\))?!?: \S.*")
SIGN_OFF = re.compile(r"Signed-off-by: [^<>\r\n]+ <[^<>\s@]+@[^<>\s@]+>", re.IGNORECASE)


def validate(message):
    errors = []
    lines = message.splitlines()
    if not lines or not SUBJECT.fullmatch(lines[0]):
        errors.append(
            'Use a Conventional Commit subject, e.g. "ci: update fork sync workflow".'
        )
    trailers = subprocess.run(
        ["git", "interpret-trailers", "--parse"],
        input=message,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.splitlines()
    if not any(SIGN_OFF.fullmatch(trailer) for trailer in trailers):
        errors.append("Add a DCO Signed-off-by trailer with git commit -s.")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("message_file", type=Path)
    args = parser.parse_args()
    errors = validate(args.message_file.read_text(encoding="utf-8"))
    for error in errors:
        print(error, file=sys.stderr)
    return bool(errors)


if __name__ == "__main__":
    sys.exit(main())

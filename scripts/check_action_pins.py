"""Require full commit SHAs for remote actions and digests for Docker actions."""

import argparse
import re
import sys
from pathlib import Path

import yaml

REMOTE_ACTION = re.compile(
    r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*@[0-9a-fA-F]{40}"
)
DOCKER_ACTION = re.compile(r"docker://[^\s@]+@sha256:[0-9a-fA-F]{64}")


def check_references(value, location=""):
    errors = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_location = f"{location}.{key}" if location else str(key)
            if key == "uses":
                if isinstance(child, str) and (
                    child.startswith("./")
                    or REMOTE_ACTION.fullmatch(child)
                    or DOCKER_ACTION.fullmatch(child)
                ):
                    continue
                errors.append(
                    f"{child_location}: pin {child!r} to a full commit SHA "
                    "(or a sha256 digest for Docker actions)."
                )
            else:
                errors.extend(check_references(child, child_location))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(check_references(child, f"{location}[{index}]"))
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()
    failed = False
    for path in args.files:
        try:
            errors = check_references(yaml.safe_load(path.read_text(encoding="utf-8")))
        except (OSError, yaml.YAMLError) as error:
            errors = [str(error)]
        for error in errors:
            print(f"{path}: {error}", file=sys.stderr)
        failed |= bool(errors)
    return failed


if __name__ == "__main__":
    sys.exit(main())

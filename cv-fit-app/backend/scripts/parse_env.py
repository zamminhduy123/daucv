#!/usr/bin/env python3
"""Minimal .env parser for Terraform external data source.

Terraform calls this script with an empty JSON object on stdin
and expects a JSON object on stdout containing the .env keys/values.

Usage: python parse_env.py  < .env.json
But we read .env directly here so Terraform just passes {}.
"""

import json
import sys
from pathlib import Path


def parse_env_file(path: Path) -> dict:
    """Parse a .env file into a dict, ignoring comments and blank lines."""
    env = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # Strip surrounding quotes if present
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        env[key] = value
    return env


def main() -> None:
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        print(json.dumps({"error": f".env not found at {env_path}"}), file=sys.stderr)
        sys.exit(1)
    result = parse_env_file(env_path)
    print(json.dumps(result))


if __name__ == "__main__":
    main()

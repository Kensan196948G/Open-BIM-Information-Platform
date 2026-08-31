#!/usr/bin/env python3
"""Validate an Open BIM /health JSON response read from stdin."""

import json
import sys
from argparse import ArgumentParser
from typing import Any


def is_healthy(payload: Any) -> bool:
    return (
        isinstance(payload, dict)
        and payload.get("status") == "ok"
        and payload.get("database") == "ok"
    )


def is_ready(payload: Any) -> bool:
    return (
        isinstance(payload, dict)
        and payload.get("status") == "ready"
        and payload.get("database") == "ok"
        and payload.get("redis") in {"ok", "disabled"}
        and payload.get("storage") == "ok"
        and payload.get("antivirus") in {"ok", "disabled"}
    )


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument("--ready", action="store_true")
    args = parser.parse_args()
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return 1
    validator = is_ready if args.ready else is_healthy
    return 0 if validator(payload) else 1


if __name__ == "__main__":
    raise SystemExit(main())

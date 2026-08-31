#!/usr/bin/env python3
"""Validate an Open BIM /health JSON response read from stdin."""

import json
import sys
from typing import Any


def is_healthy(payload: Any) -> bool:
    return (
        isinstance(payload, dict)
        and payload.get("status") == "ok"
        and payload.get("database") == "ok"
    )


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return 1
    return 0 if is_healthy(payload) else 1


if __name__ == "__main__":
    raise SystemExit(main())

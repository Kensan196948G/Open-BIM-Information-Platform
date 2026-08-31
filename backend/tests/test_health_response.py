import json
import subprocess
import sys
from pathlib import Path

import pytest

HEALTH_VALIDATOR = (
    Path(__file__).resolve().parents[2] / "scripts" / "validate_health_response.py"
)


@pytest.mark.no_db
@pytest.mark.parametrize(
    ("payload", "expected_code"),
    [
        ({"status": "ok", "database": "ok", "redis": "ok"}, 0),
        ({"status": "ok", "database": "ok", "redis": "unavailable"}, 0),
        ({"status": "degraded", "database": "error"}, 1),
        ("<!doctype html><title>Open BIM</title>", 1),
    ],
)
def test_health_response_validator(payload: object, expected_code: int):
    input_text = payload if isinstance(payload, str) else json.dumps(payload)
    result = subprocess.run(
        [sys.executable, str(HEALTH_VALIDATOR)],
        input=input_text,
        text=True,
        check=False,
    )
    assert result.returncode == expected_code


@pytest.mark.no_db
@pytest.mark.parametrize(
    ("payload", "expected_code"),
    [
        (
            {
                "status": "ready",
                "database": "ok",
                "redis": "ok",
                "storage": "ok",
                "antivirus": "ok",
            },
            0,
        ),
        (
            {
                "status": "ready",
                "database": "ok",
                "redis": "disabled",
                "storage": "ok",
                "antivirus": "disabled",
            },
            0,
        ),
        (
            {
                "status": "not_ready",
                "database": "ok",
                "redis": "ok",
                "storage": "unavailable",
                "antivirus": "ok",
            },
            1,
        ),
    ],
)
def test_readiness_response_validator(payload: object, expected_code: int):
    result = subprocess.run(
        [sys.executable, str(HEALTH_VALIDATOR), "--ready"],
        input=json.dumps(payload),
        text=True,
        check=False,
    )
    assert result.returncode == expected_code

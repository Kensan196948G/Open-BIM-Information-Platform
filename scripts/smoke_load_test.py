#!/usr/bin/env python3
"""Smoke load test for the Open BIM platform (no external dependencies).

Usage (against a seeded/staging backend):
    python3 scripts/smoke_load_test.py --base-url http://127.0.0.1:8000 \
        --users 20 --iterations 10

Measures p50/p95 latency and error rate for:
  /health, login, GET /projects, GET /notifications, GET /workflows/tasks/mine
"""

import argparse
import asyncio
import statistics
import time

import httpx


async def worker(
    base_url: str,
    email: str,
    password: str,
    iterations: int,
    results: list[dict],
    verify: bool,
) -> None:
    async with httpx.AsyncClient(base_url=base_url, timeout=15, verify=verify) as client:
        login_start = time.perf_counter()
        try:
            login = await client.post(
                "/api/v1/auth/login",
                data={"username": email, "password": password},
            )
            token = login.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            results.append(
                {
                    "op": "login",
                    "latency": (time.perf_counter() - login_start) * 1000,
                    "status": login.status_code,
                }
            )
        except Exception:
            results.append({"op": "login", "latency": -1, "status": 0})
            return

        for _ in range(iterations):
            for op, method, path, kwargs in (
                ("health", "get", "/health", {}),
                ("projects", "get", "/api/v1/projects", {"headers": headers}),
                (
                    "notifications",
                    "get",
                    "/api/v1/notifications?size=5",
                    {"headers": headers},
                ),
                (
                    "tasks",
                    "get",
                    "/api/v1/workflows/tasks/mine",
                    {"headers": headers},
                ),
            ):
                start = time.perf_counter()
                try:
                    response = await getattr(client, method)(path, **kwargs)
                    latency = (time.perf_counter() - start) * 1000
                    results.append(
                        {"op": op, "latency": latency, "status": response.status_code}
                    )
                except Exception:
                    results.append({"op": op, "latency": -1, "status": 0})


def summarize(results: list[dict], label: str) -> None:
    ops = sorted({r["op"] for r in results})
    print(f"\n=== {label} ===")
    for op in ops:
        rows = [r for r in results if r["op"] == op]
        ok = [r["latency"] for r in rows if r["latency"] >= 0 and r["status"] < 500]
        errors = len(rows) - len(ok)
        if ok:
            p50 = statistics.median(ok)
            p95 = sorted(ok)[int(len(ok) * 0.95) - 1]
            print(
                f"{op:14s} n={len(rows):4d} p50={p50:7.1f}ms "
                f"p95={p95:7.1f}ms errors={errors}"
            )
        else:
            print(f"{op:14s} n={len(rows):4d} all failed (errors={errors})")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--users", type=int, default=20)
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--email", default="e2e@test.example.com")
    parser.add_argument("--password", default="TestPass123!")
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS verification (self-signed staging certs)",
    )
    args = parser.parse_args()

    results: list[dict] = []
    verify = not args.insecure
    tasks = [
        asyncio.create_task(
            worker(
                args.base_url,
                args.email,
                args.password,
                args.iterations,
                results,
                verify,
            )
        )
        for _ in range(args.users)
    ]
    await asyncio.gather(*tasks)
    summarize(results, f"{args.users} users × {args.iterations} iterations")


if __name__ == "__main__":
    asyncio.run(main())

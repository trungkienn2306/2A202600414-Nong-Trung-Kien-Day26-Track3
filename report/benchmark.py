from __future__ import annotations

import asyncio
import json
import statistics
import sys
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastmcp import Client  # noqa: E402

from src.db import SQLiteRepository  # noqa: E402
from src.init_db import create_database  # noqa: E402
from src import mcp_server  # noqa: E402

DB_PATH = ROOT / "data" / "benchmark.sqlite3"
OUTPUT_PATH = Path(__file__).resolve().parent / "benchmark_results.json"
ITERATIONS = 100
MCP_ITERATIONS = 30


def timed_sync(label: str, iterations: int, action: Callable[[int], Any]) -> dict[str, Any]:
    durations = []
    for index in range(iterations):
        start = time.perf_counter()
        action(index)
        durations.append((time.perf_counter() - start) * 1000)
    return summarize(label, iterations, durations)


async def timed_async(
    label: str, iterations: int, action: Callable[[int], Awaitable[Any]]
) -> dict[str, Any]:
    durations = []
    for index in range(iterations):
        start = time.perf_counter()
        await action(index)
        durations.append((time.perf_counter() - start) * 1000)
    return summarize(label, iterations, durations)


def summarize(label: str, iterations: int, durations: list[float]) -> dict[str, Any]:
    total_ms = sum(durations)
    return {
        "label": label,
        "iterations": iterations,
        "total_ms": round(total_ms, 3),
        "mean_ms": round(statistics.mean(durations), 3),
        "median_ms": round(statistics.median(durations), 3),
        "min_ms": round(min(durations), 3),
        "max_ms": round(max(durations), 3),
        "p95_ms": round(percentile(durations, 95), 3),
        "ops_per_second": round(iterations / (total_ms / 1000), 2),
    }


def percentile(values: list[float], percentile_value: int) -> float:
    ordered = sorted(values)
    index = (len(ordered) - 1) * (percentile_value / 100)
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


async def main() -> None:
    create_database(DB_PATH)
    repository = SQLiteRepository(DB_PATH)
    mcp_server.repository = repository
    results = []

    results.append(
        timed_sync(
            "repository.search filtered ordered limit=10",
            ITERATIONS,
            lambda _: repository.search(
                "students", filters={"cohort": "A1"}, limit=10, order_by="score", descending=True
            ),
        )
    )
    results.append(
        timed_sync(
            "repository.aggregate avg(score) group_by cohort",
            ITERATIONS,
            lambda _: repository.aggregate("students", "avg", "score", group_by="cohort"),
        )
    )
    results.append(
        timed_sync(
            "repository.schema full database",
            ITERATIONS,
            lambda _: repository.full_schema(),
        )
    )
    results.append(
        timed_sync(
            "repository.schema students table",
            ITERATIONS,
            lambda _: repository.table_schema("students"),
        )
    )
    results.append(
        timed_sync(
            "repository.insert student",
            30,
            lambda index: repository.insert(
                "students",
                {
                    "name": f"Benchmark Student {index}",
                    "cohort": "BENCH",
                    "age": 25,
                    "email": f"bench{index}@example.com",
                    "score": 90.0 + (index % 10),
                },
            ),
        )
    )

    async with Client(mcp_server.mcp) as client:
        results.append(
            await timed_async(
                "mcp.in_process.client list_tools",
                MCP_ITERATIONS,
                lambda _: client.list_tools(),
            )
        )
        results.append(
            await timed_async(
                "mcp.in_process.client read schema://database",
                MCP_ITERATIONS,
                lambda _: client.read_resource("schema://database"),
            )
        )
        results.append(
            await timed_async(
                "mcp.in_process.client call search",
                MCP_ITERATIONS,
                lambda _: client.call_tool(
                    "search",
                    {"table": "students", "filters": {"cohort": "A1"}, "limit": 10},
                ),
            )
        )
        results.append(
            await timed_async(
                "mcp.in_process.client call aggregate",
                MCP_ITERATIONS,
                lambda _: client.call_tool(
                    "aggregate",
                    {"table": "students", "metric": "avg", "column": "score", "group_by": "cohort"},
                ),
            )
        )

    payload = {
        "iterations": {"repository": ITERATIONS, "mcp_client": MCP_ITERATIONS},
        "database": str(DB_PATH),
        "results": results,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

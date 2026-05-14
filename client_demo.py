from __future__ import annotations

import asyncio
import json
from typing import Any

from fastmcp import Client

from src.init_db import create_database
from src.mcp_server import mcp


def normalize_result(result: Any) -> Any:
    if hasattr(result, "data"):
        return result.data
    if isinstance(result, list) and result and hasattr(result[0], "text"):
        try:
            return json.loads(result[0].text)
        except json.JSONDecodeError:
            return result[0].text
    return result


def print_section(title: str, payload: object) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


async def main() -> None:
    create_database()
    async with Client(mcp) as client:
        print_section("discovered tools", [tool.name for tool in await client.list_tools()])
        print_section(
            "schema://database", normalize_result(await client.read_resource("schema://database"))
        )
        print_section(
            "schema://table/students",
            normalize_result(await client.read_resource("schema://table/students")),
        )
        print_section(
            "search students cohort A1",
            normalize_result(
                await client.call_tool(
                    "search",
                    {
                        "table": "students",
                        "filters": {"cohort": "A1"},
                        "limit": 2,
                        "order_by": "score",
                        "descending": True,
                    },
                )
            ),
        )
        print_section(
            "insert new student",
            normalize_result(
                await client.call_tool(
                    "insert",
                    {
                        "table": "students",
                        "values": {
                            "name": "Demo Student",
                            "cohort": "D4",
                            "age": 24,
                            "email": "demo.student@example.com",
                            "score": 93.5,
                        },
                    },
                )
            ),
        )
        print_section(
            "aggregate avg score by cohort",
            normalize_result(
                await client.call_tool(
                    "aggregate",
                    {"table": "students", "metric": "avg", "column": "score", "group_by": "cohort"},
                )
            ),
        )
        print_section(
            "expected failure: invalid table",
            normalize_result(await client.call_tool("search", {"table": "missing_table"})),
        )
        print_section(
            "expected failure: bad aggregate",
            normalize_result(
                await client.call_tool(
                    "aggregate", {"table": "students", "metric": "median", "column": "score"}
                )
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())

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


async def main() -> None:
    create_database()
    async with Client(mcp) as client:
        tools = await client.list_tools()
        resources = await client.list_resources()
        templates = await client.list_resource_templates()

        print("TOOLS:", [tool.name for tool in tools])
        print("RESOURCES:", [str(resource.uri) for resource in resources])
        print("RESOURCE_TEMPLATES:", [template.uriTemplate for template in templates])

        search_result = await client.call_tool(
            "search", {"table": "students", "limit": 2, "order_by": "score", "descending": True}
        )
        aggregate_result = await client.call_tool(
            "aggregate",
            {"table": "students", "metric": "avg", "column": "score", "group_by": "cohort"},
        )
        invalid_result = await client.call_tool("search", {"table": "missing_table"})
        schema_result = await client.read_resource("schema://database")
        table_schema_result = await client.read_resource("schema://table/students")

        print("SEARCH_OK:", normalize_result(search_result))
        print("AGGREGATE_OK:", normalize_result(aggregate_result))
        print("INVALID_SEARCH:", normalize_result(invalid_result))
        print("SCHEMA_PREFIX:", str(normalize_result(schema_result))[:160])
        print("TABLE_SCHEMA_PREFIX:", str(normalize_result(table_schema_result))[:160])


if __name__ == "__main__":
    asyncio.run(main())

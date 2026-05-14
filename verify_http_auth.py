from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from fastmcp import Client


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
    url = os.getenv("MCP_HTTP_URL", "http://127.0.0.1:8000/mcp")
    token = os.environ["MCP_AUTH_TOKEN"]
    async with Client(url, auth=token) as client:
        tools = await client.list_tools()
        resources = await client.list_resources()
        templates = await client.list_resource_templates()
        search_result = await client.call_tool(
            "search", {"table": "students", "filters": {"cohort": "A1"}, "limit": 2}
        )
        aggregate_result = await client.call_tool(
            "aggregate",
            {"table": "students", "metric": "avg", "column": "score", "group_by": "cohort"},
        )
        invalid_result = await client.call_tool("search", {"table": "missing_table"})
        table_schema = await client.read_resource("schema://table/students")

        print("AUTH_HTTP_TOOLS:", [tool.name for tool in tools])
        print("AUTH_HTTP_RESOURCES:", [str(resource.uri) for resource in resources])
        print("AUTH_HTTP_RESOURCE_TEMPLATES:", [template.uriTemplate for template in templates])
        print("AUTH_HTTP_SEARCH_OK:", normalize_result(search_result))
        print("AUTH_HTTP_AGGREGATE_OK:", normalize_result(aggregate_result))
        print("AUTH_HTTP_INVALID_SEARCH:", normalize_result(invalid_result))
        print("AUTH_HTTP_TABLE_SCHEMA_PREFIX:", str(normalize_result(table_schema))[:160])


if __name__ == "__main__":
    asyncio.run(main())

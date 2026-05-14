from __future__ import annotations

import argparse
import json
import os
from typing import Any

from fastmcp import FastMCP

from src.db import SQLiteRepository
from src.init_db import DEFAULT_DB_PATH
from src.repository import DatabaseRepository, PostgresRepository
from src.validation import ValidationError


def create_auth_provider() -> Any | None:
    token = os.getenv("MCP_AUTH_TOKEN")
    if not token:
        return None
    from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

    return StaticTokenVerifier(
        tokens={token: {"client_id": "lab-demo-client", "scopes": ["read", "write"]}}
    )


mcp = FastMCP("Database Lab MCP Server", auth=create_auth_provider())


def create_repository() -> DatabaseRepository:
    postgres_dsn = os.getenv("POSTGRES_DSN")
    if postgres_dsn:
        return PostgresRepository(postgres_dsn)
    return SQLiteRepository(os.getenv("SQLITE_DB_PATH", str(DEFAULT_DB_PATH)))


repository = create_repository()


def success(data: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, **data}


def failure(error: Exception) -> dict[str, Any]:
    return {"ok": False, "error": str(error), "error_type": type(error).__name__}


def database_failure() -> dict[str, Any]:
    return {"ok": False, "error": "Database request failed", "error_type": "DatabaseError"}


@mcp.tool(name="search")
def search(
    table: str,
    filters: Any = None,
    columns: list[str] | None = None,
    limit: int = 20,
    offset: int = 0,
    order_by: str | None = None,
    descending: bool = False,
) -> dict[str, Any]:
    try:
        return success(
            repository.search(
                table=table,
                filters=filters,
                columns=columns,
                limit=limit,
                offset=offset,
                order_by=order_by,
                descending=descending,
            )
        )
    except ValidationError as error:
        return failure(error)
    except Exception:
        return database_failure()


@mcp.tool(name="insert")
def insert(table: str, values: dict[str, Any]) -> dict[str, Any]:
    try:
        return success(repository.insert(table, values))
    except ValidationError as error:
        return failure(error)
    except Exception:
        return database_failure()


@mcp.tool(name="aggregate")
def aggregate(
    table: str,
    metric: str,
    column: str | None = None,
    filters: Any = None,
    group_by: str | list[str] | None = None,
) -> dict[str, Any]:
    try:
        return success(repository.aggregate(table, metric, column, filters, group_by))
    except ValidationError as error:
        return failure(error)
    except Exception:
        return database_failure()


@mcp.resource("schema://database")
def database_schema() -> str:
    try:
        payload = repository.full_schema()
    except Exception:
        payload = database_failure()
    return json.dumps(payload, indent=2, ensure_ascii=False)


@mcp.resource("schema://table/{table_name}")
def table_schema(table_name: str) -> str:
    try:
        payload = {table_name: repository.table_schema(table_name)}
    except ValidationError as error:
        payload = failure(error)
    except Exception:
        payload = database_failure()
    return json.dumps(payload, indent=2, ensure_ascii=False)


def require_auth_token(transport: str) -> None:
    if transport in {"http", "sse"} and not os.getenv("MCP_AUTH_TOKEN"):
        raise SystemExit(
            "MCP_AUTH_TOKEN must be set before running authenticated HTTP/SSE transport"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the SQLite Lab FastMCP server")
    parser.add_argument("--transport", choices=["stdio", "http", "sse"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--path", default="/mcp")
    return parser.parse_args()


def run() -> None:
    args = parse_args()
    require_auth_token(args.transport)
    if args.transport == "stdio":
        mcp.run()
        return
    mcp.run(transport=args.transport, host=args.host, port=args.port, path=args.path)


if __name__ == "__main__":
    run()

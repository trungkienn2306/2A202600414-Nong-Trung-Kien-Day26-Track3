from __future__ import annotations

import json

from src import mcp_server


def test_mcp_tool_wrappers_return_structured_success(repository, monkeypatch):
    monkeypatch.setattr(mcp_server, "repository", repository)

    result = mcp_server.search(
        "students", filters={"cohort": "A1"}, limit=2, order_by="score", descending=True
    )

    assert result["ok"] is True
    assert result["count"] == 2
    assert result["rows"][0]["name"] == "Binh Tran"


def test_mcp_tool_wrappers_return_structured_errors(repository, monkeypatch):
    monkeypatch.setattr(mcp_server, "repository", repository)

    result = mcp_server.aggregate("students", "median", "score")

    assert result["ok"] is False
    assert result["error_type"] == "ValidationError"
    assert "Unsupported aggregate" in result["error"]


def test_schema_resources(repository, monkeypatch):
    monkeypatch.setattr(mcp_server, "repository", repository)

    full_schema = json.loads(mcp_server.database_schema())
    table_schema = json.loads(mcp_server.table_schema("students"))

    assert set(full_schema) == {"courses", "enrollments", "students"}
    assert table_schema["students"][0]["name"] == "id"


def test_invalid_table_resource_returns_clear_error(repository, monkeypatch):
    monkeypatch.setattr(mcp_server, "repository", repository)

    result = json.loads(mcp_server.table_schema("missing"))

    assert result["ok"] is False
    assert result["error_type"] == "ValidationError"

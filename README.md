# Day 26 Track 3 - FastMCP Database Server

This submission implements a FastMCP server that exposes a reproducible SQLite database through MCP tools and resources.

## Features

- FastMCP server with stdio transport by default.
- Optional authenticated HTTP/SSE transport using bearer token auth.
- Reproducible SQLite database with `students`, `courses`, and `enrollments` tables.
- Shared repository interface with a working SQLite adapter and PostgreSQL-ready adapter boundary.
- Required MCP tools:
  - `search`
  - `insert`
  - `aggregate`
- Required MCP resources:
  - `schema://database`
  - `schema://table/{table_name}`
- Safe validation for table names, column names, filter operators, aggregate metrics, inserts, ordering, and pagination.
- Repeatable pytest, MCP discovery, client demo, and HTTP auth verification scripts.

## Project Structure

```text
src/
  __init__.py
  db.py              # SQLite repository and safe SQL execution
  init_db.py         # deterministic schema and seed data
  mcp_server.py      # FastMCP tools/resources/transports
  repository.py      # shared repository interface and PostgreSQL boundary
  validation.py      # input validation and allowed operators/metrics
tests/
  conftest.py
  test_mcp_server.py
  test_repository.py
client_demo.py       # FastMCP client demo for success/failure cases
verify_mcp.py        # FastMCP in-memory client discovery and tool calls
verify_http_auth.py  # authenticated HTTP transport verification client
requirements.txt
Rubric.md
Tips.md
```

## Setup

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Initialize the database:

```powershell
.\.venv\Scripts\python.exe -m src.init_db
```

Expected output:

```text
Initialized SQLite database at ...\data\lab.sqlite3
```

## Run the MCP Server

Default stdio transport:

```powershell
.\.venv\Scripts\python.exe -m src.mcp_server
```

Authenticated HTTP transport bonus:

```powershell
$env:MCP_AUTH_TOKEN = "lab-demo-token"
.\.venv\Scripts\python.exe -m src.mcp_server --transport http --host 127.0.0.1 --port 8000 --path /mcp
```

Authenticated SSE transport bonus:

```powershell
$env:MCP_AUTH_TOKEN = "lab-demo-token"
.\.venv\Scripts\python.exe -m src.mcp_server --transport sse --host 127.0.0.1 --port 8000 --path /mcp
```

The HTTP/SSE server uses FastMCP `StaticTokenVerifier`; clients must send `Authorization: Bearer lab-demo-token`.

## Tool Reference

### `search`

Arguments:

```json
{
  "table": "students",
  "filters": {"cohort": "A1"},
  "columns": ["name", "score"],
  "limit": 10,
  "offset": 0,
  "order_by": "score",
  "descending": true
}
```

Supported filter operators:

```text
eq, ne, gt, gte, lt, lte, like, in
```

Filter forms:

```json
{"cohort": "A1"}
```

```json
{"score": {"operator": "gte", "value": 85}}
```

```json
[
  {"column": "cohort", "operator": "in", "value": ["A1", "B2"]},
  {"column": "name", "operator": "like", "value": "%n%"}
]
```

### `insert`

Arguments:

```json
{
  "table": "students",
  "values": {
    "name": "Demo Student",
    "cohort": "D4",
    "age": 24,
    "email": "demo.student@example.com",
    "score": 93.5
  }
}
```

Returns the inserted payload, including generated `id`.

### `aggregate`

Arguments:

```json
{
  "table": "students",
  "metric": "avg",
  "column": "score",
  "group_by": "cohort"
}
```

Supported metrics:

```text
count, avg, sum, min, max
```

`count` supports `column = null` and uses `COUNT(*)`. `avg` and `sum` require numeric columns.

## MCP Resources

Full database schema:

```text
schema://database
```

Single table schema template:

```text
schema://table/{table_name}
```

Example:

```text
schema://table/students
```

## Verification Commands

Run unit/integration tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Verified result in this environment:

```text
15 passed in 2.13s
```

Run coverage:

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=src --cov-report=term-missing
```

Verified result in this environment:

```text
TOTAL 81%
```

Run MCP client demo:

```powershell
.\.venv\Scripts\python.exe client_demo.py
```

The demo uses `fastmcp.Client` against the local FastMCP server object and prints:

- `schema://database`
- `schema://table/students`
- successful `search`
- successful `insert`
- successful grouped `aggregate`
- expected failure for invalid table
- expected failure for bad aggregate

Run code quality checks:

```powershell
.\.venv\Scripts\python.exe -m black --check src tests client_demo.py verify_mcp.py verify_http_auth.py
.\.venv\Scripts\python.exe -m ruff check src tests client_demo.py verify_mcp.py verify_http_auth.py
.\.venv\Scripts\python.exe -m mypy src client_demo.py verify_mcp.py verify_http_auth.py
```

Run MCP discovery and tool-call verification:

```powershell
.\.venv\Scripts\python.exe verify_mcp.py
```

Verified output includes:

```text
TOOLS: ['search', 'insert', 'aggregate']
RESOURCES: ['schema://database']
RESOURCE_TEMPLATES: ['schema://table/{table_name}']
TABLE_SCHEMA_PREFIX: {'students': ...}
INVALID_SEARCH: {'ok': False, 'error': "Unknown table ...", 'error_type': 'ValidationError'}
```

Run authenticated HTTP verification:

Terminal 1:

```powershell
$env:MCP_AUTH_TOKEN = "lab-demo-token"
.\.venv\Scripts\python.exe -m src.mcp_server --transport http --host 127.0.0.1 --port 8000 --path /mcp
```

Terminal 2:

```powershell
$env:MCP_AUTH_TOKEN = "lab-demo-token"
$env:MCP_HTTP_URL = "http://127.0.0.1:8000/mcp"
.\.venv\Scripts\python.exe verify_http_auth.py
```

Verified output:

```text
AUTH_HTTP_TOOLS: ['search', 'insert', 'aggregate']
```

## MCP Inspector

```powershell
npx -y @modelcontextprotocol/inspector .\.venv\Scripts\python.exe -m src.mcp_server
```

Checklist inside Inspector:

1. Confirm tools: `search`, `insert`, `aggregate`.
2. Confirm resources: `schema://database`, `schema://table/{table_name}`.
3. Call `search` with `table = students` and `filters = {"cohort": "A1"}`.
4. Call `insert` with a new student payload.
5. Call `aggregate` with `metric = avg`, `column = score`, `group_by = cohort`.
6. Call `search` with an invalid table and confirm a clear validation error.

## Claude Code Client Configuration

Example `.mcp.json`:

```json
{
  "mcpServers": {
    "sqlite-lab": {
      "type": "stdio",
      "command": "E:\\LabAIThucChien\\2A202600414-Nong-Trung-Kien-Day26-Track3\\.venv\\Scripts\\python.exe",
      "args": [
        "-m",
        "src.mcp_server"
      ],
      "cwd": "E:\\LabAIThucChien\\2A202600414-Nong-Trung-Kien-Day26-Track3"
    }
  }
}
```

Example prompts after connecting:

```text
Use sqlite-lab to read schema://database.
Use sqlite-lab to search students in cohort A1 ordered by score descending.
Use sqlite-lab to compute avg score grouped by cohort.
Use sqlite-lab to insert a new student and return the inserted payload.
```

## Gemini CLI Client Configuration

```powershell
gemini mcp add sqlite-lab E:\LabAIThucChien\2A202600414-Nong-Trung-Kien-Day26-Track3\.venv\Scripts\python.exe -m src.mcp_server --description "SQLite lab FastMCP server" --timeout 10000
```

Then verify:

```powershell
gemini mcp list
gemini --allowed-mcp-server-names sqlite-lab --yolo -p "Use the sqlite-lab MCP server and show the top 2 students by score."
```

## Safety Notes

- Table and column names are never accepted directly into SQL unless they match the introspected schema allowlist.
- User values are bound through SQLite parameters.
- Unsupported operators and aggregate metrics return clear `ValidationError` responses.
- `limit` is bounded to `1..100` to avoid oversized outputs.
- HTTP/SSE auth tokens are read from `MCP_AUTH_TOKEN`; no secrets are hardcoded.

## Rubric Mapping

| Rubric item | Evidence |
|---|---|
| FastMCP server starts | `python -m src.mcp_server`; `verify_mcp.py` imports and uses the server |
| Clean project structure | `src/`, `tests/`, demo/verification scripts, `.gitignore` |
| SQLite reproducible schema/data | `src/init_db.py`, `python -m src.init_db` |
| Server/database separation | `src/mcp_server.py` delegates to `src/db.py` through repository shape |
| `search` filters/order/pagination | `SQLiteRepository.search`, `tests/test_repository.py` |
| `insert` returns inserted payload | `SQLiteRepository.insert`, `client_demo.py` |
| `aggregate` count/avg/sum/min/max | `SQLiteRepository.aggregate`, parametrized pytest |
| Full schema resource | `schema://database`, `database_schema()` |
| Per-table schema template | `schema://table/{table_name}`, `table_schema()` |
| Reject invalid table/column | validation tests and structured MCP error response |
| Reject bad operators/aggregates | validation tests and `verify_mcp.py` invalid call |
| Safe parameterized SQL | bound values in `src/db.py`, identifier allowlisting |
| Tool discovery verified | `verify_mcp.py` lists `['search', 'insert', 'aggregate']` |
| Successful tool calls demonstrated | MCP client calls in `client_demo.py`, `verify_mcp.py` |
| Failing tool calls demonstrated | MCP client calls in `client_demo.py`, `verify_mcp.py` |
| MCP client configured | Claude Code and Gemini examples above |
| Setup/test steps | README setup and verification sections |
| Demo/screenshots equivalent | repeatable demo scripts and Inspector checklist |

## Bonus Mapping

| Bonus item | Evidence |
|---|---|
| HTTP/SSE auth | `MCP_AUTH_TOKEN`, `StaticTokenVerifier`, `verify_http_auth.py` |
| SQLite/PostgreSQL shared interface | `src/repository.py` `DatabaseRepository` protocol and `PostgresRepository` boundary |
| Extra polish | output limit, pagination, structured errors, pytest coverage, MCP discovery script |

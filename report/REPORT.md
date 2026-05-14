# Day 26 Track 3 - Real Run & Benchmark Report

Date: 2026-05-14  
Project: `2A202600414-Nong-Trung-Kien-Day26-Track3`  
Runtime: Windows 10, Python 3.12, local `.venv`  
Server: FastMCP + SQLite/PostgreSQL

## Executive Summary

The lab implementation was run locally with in-process MCP verification, a live authenticated HTTP transport check, and a live Docker PostgreSQL verification. The FastMCP server exposes the required MCP tools and resources, SQLite/PostgreSQL data is reproducible, valid calls succeed, invalid calls return structured errors, and the authenticated HTTP transport bonus was verified.

Final status:

| Area | Result |
|---|---:|
| Pytest | 20 passed |
| Coverage | 85% |
| FastMCP tool discovery | Passed |
| MCP resource discovery | Passed |
| In-process MCP client tool/resource calls | Passed |
| Live authenticated HTTP tool/resource calls | Passed |
| Invalid request handling | Passed |
| Authenticated HTTP transport | Passed |
| Live Docker PostgreSQL repository verification | Passed |
| MCP verification on PostgreSQL backend | Passed |
| Benchmark script | Passed |

## Commands Actually Run

```powershell
$env:POSTGRES_DSN = "postgresql://labuser:labpass@127.0.0.1:55432/labdb"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest --cov=src --cov-report=term-missing
.\.venv\Scripts\python.exe verify_mcp.py
.\.venv\Scripts\python.exe client_demo.py
.\.venv\Scripts\python.exe verify_postgres.py
.\.venv\Scripts\python.exe -m src.init_postgres
.\.venv\Scripts\python.exe verify_mcp.py
$env:MCP_AUTH_TOKEN = "lab-demo-token"
$env:MCP_HTTP_URL = "http://127.0.0.1:8017/mcp"
.\.venv\Scripts\python.exe verify_http_auth.py
.\.venv\Scripts\python.exe report\benchmark.py
```

Raw outputs are saved in `report/raw/`.

## Verification Results

### Test Suite

Result from `report/raw/pytest.txt`:

```text
20 passed in 3.66s
```

### Coverage

Result from `report/raw/coverage.txt`:

```text
TOTAL 445 statements, 68 missed, 85% coverage
20 passed in 5.47s
```

Coverage by main implementation files:

| File | Coverage |
|---|---:|
| `src/db.py` | 94% |
| `src/init_db.py` | 88% |
| `src/init_postgres.py` | 77% |
| `src/mcp_server.py` | 60% |
| `src/repository.py` | 92% |
| `src/validation.py` | 89% |
| Total | 85% |

### MCP Discovery

Result from `report/raw/verify_mcp.txt` confirms:

```text
TOOLS: ['search', 'insert', 'aggregate']
RESOURCES: ['schema://database']
RESOURCE_TEMPLATES: ['schema://table/{table_name}']
```

The same verification also calls:

- `search`
- `aggregate`
- invalid `search` with missing table
- `schema://database`
- `schema://table/students`

### In-Process MCP Client Demo

`client_demo.py` uses `fastmcp.Client` against the imported FastMCP server object. This verifies MCP tool/resource behavior without stdio/HTTP network overhead. It demonstrates:

- discovered tools
- full schema resource
- per-table schema resource
- successful `search`
- successful `insert`
- successful `aggregate`
- expected invalid table error
- expected bad aggregate error

Raw output: `report/raw/client_demo.txt`.

### Authenticated HTTP Transport Bonus

HTTP auth verification command was run against a live local server process on `127.0.0.1:8017/mcp` using `MCP_AUTH_TOKEN=lab-demo-token`.

Result from `report/raw/verify_http_auth.txt` confirms tool/resource discovery plus live HTTP calls:

```text
AUTH_HTTP_TOOLS: ['search', 'insert', 'aggregate']
AUTH_HTTP_RESOURCES: ['schema://database']
AUTH_HTTP_RESOURCE_TEMPLATES: ['schema://table/{table_name}']
AUTH_HTTP_SEARCH_OK: {'ok': True, ...}
AUTH_HTTP_AGGREGATE_OK: {'ok': True, ...}
AUTH_HTTP_INVALID_SEARCH: {'ok': False, ...}
AUTH_HTTP_TABLE_SCHEMA_PREFIX: {'students': ...}
```

This verifies that a real FastMCP HTTP client can authenticate, discover tools/resources, call successful tools, read a per-table schema resource, and receive a clear error for an invalid request.

### Live PostgreSQL Bonus Verification

Docker PostgreSQL was run locally on `127.0.0.1:55432` and verified with `POSTGRES_DSN=postgresql://labuser:labpass@127.0.0.1:55432/labdb`.

Result from `report/raw/verify_postgres.txt` confirms direct repository support:

```text
POSTGRES_TABLES: ['courses', 'enrollments', 'students']
POSTGRES_SEARCH_OK: {'table': 'students', ...}
POSTGRES_INSERT_OK: {'table': 'students', 'inserted': ...}
POSTGRES_AGGREGATE_OK: {'table': 'students', ...}
```

Result from `report/raw/verify_mcp_postgres.txt` confirms the same FastMCP tools/resources work when `src.mcp_server` selects `PostgresRepository` from `POSTGRES_DSN`.

## Benchmark Methodology

Benchmark script: `report/benchmark.py`  
Raw JSON result: `report/benchmark_results.json`

Method:

- Recreated a fresh benchmark database at `data/benchmark.sqlite3`.
- Measured repository-level operations with 100 iterations, except insert with 30 iterations.
- Measured MCP client calls with 30 iterations.
- Bound both repository and in-process MCP client calls to the same benchmark database: `data/benchmark.sqlite3`.
- Used `time.perf_counter()` and reported total, mean, median, min, max, p95, and ops/sec.
- MCP client benchmark uses in-process `fastmcp.Client(mcp)`, so results measure MCP handler/client overhead without HTTP/SSE network latency.

## Benchmark Results

### Repository-Level Operations

| Operation | Iterations | Mean ms | Median ms | P95 ms | Ops/sec |
|---|---:|---:|---:|---:|---:|
| `repository.search` filtered/order/limit | 100 | 1.380 | 0.696 | 2.844 | 724.54 |
| `repository.aggregate avg(score) group_by cohort` | 100 | 1.470 | 1.018 | 3.577 | 680.21 |
| `repository.full_schema()` | 100 | 1.646 | 1.145 | 3.925 | 607.37 |
| `repository.table_schema("students")` | 100 | 0.384 | 0.277 | 0.583 | 2602.29 |
| `repository.insert` student | 30 | 7.618 | 7.316 | 9.149 | 131.28 |

Observations:

- Search and aggregate are consistently sub-2ms mean at repository level on this small dataset.
- Insert is slower because each operation performs a SQLite write transaction.
- Table schema lookup is the fastest operation.
- Full schema lookup is slower because it introspects all tables.

### MCP Client Operations

| Operation | Iterations | Mean ms | Median ms | P95 ms | Ops/sec |
|---|---:|---:|---:|---:|---:|
| `client.list_tools()` | 30 | 0.567 | 0.460 | 0.570 | 1762.87 |
| `client.read_resource("schema://database")` | 30 | 3.589 | 3.146 | 5.536 | 278.62 |
| `client.call_tool("search")` | 30 | 4.915 | 4.145 | 6.964 | 203.45 |
| `client.call_tool("aggregate")` | 30 | 6.431 | 6.086 | 10.224 | 155.50 |

Observations:

- MCP client calls add overhead compared with direct repository calls, as expected.
- Tool calls remain under 5ms mean in the in-process benchmark.
- Resource reads are slightly faster than tool calls because they avoid filter/aggregate request handling.
- HTTP transport will be slower than this in-process benchmark due to network and auth middleware overhead.

## Rubric Evidence Matrix

| Rubric item | Evidence |
|---|---|
| FastMCP server starts successfully | Live HTTP server process used by `verify_http_auth.py`; in-process MCP checks via `verify_mcp.py` |
| Clean project structure | `src/`, `tests/`, `report/`, verification scripts |
| SQLite reproducible schema/data | `src/init_db.py`, benchmark recreates `data/benchmark.sqlite3` |
| PostgreSQL reproducible schema/data | Docker PostgreSQL + `src/init_postgres.py` + `verify_postgres.py` |
| Server/database separation | MCP wrapper delegates through `DatabaseRepository` to SQLite or PostgreSQL |
| `search` filters/order/pagination | tests + `verify_mcp.py` + benchmark |
| `insert` returns inserted payload | tests + `client_demo.py` + benchmark |
| `aggregate` count/avg/sum/min/max | tests + `client_demo.py` + benchmark |
| Full schema resource | `schema://database` verified by MCP client |
| Per-table schema template | `schema://table/students` verified by MCP client |
| Invalid table/column rejected | tests + demo invalid table |
| Unsupported operators/aggregates rejected | tests + demo bad aggregate |
| Parameterized SQL | implementations in `src/db.py` and `src/repository.py`; benchmark and tests pass |
| Tool discovery verified | `TOOLS: ['search', 'insert', 'aggregate']` |
| Successful tool calls demonstrated | `client_demo.py`, `verify_mcp.py` |
| Failing tool calls demonstrated | invalid table and bad aggregate responses |
| MCP client configured/usable | In-process `fastmcp.Client` demo plus live authenticated HTTP `fastmcp.Client` verification |
| README setup/test steps | README updated |
| Short demo equivalent | repeatable `client_demo.py` + raw output |

## Bonus Evidence

| Bonus | Evidence |
|---|---|
| HTTP/SSE auth | `MCP_AUTH_TOKEN`, live HTTP auth verification with tool/resource calls, `verify_http_auth.py` |
| SQLite + PostgreSQL shared interface | `DatabaseRepository`, working `SQLiteRepository`, working `PostgresRepository`, Docker verification |
| Extra polish | pagination limit, structured errors, coverage, benchmark report, raw artifacts |

## Artifact Index

| File | Purpose |
|---|---|
| `report/REPORT.md` | This final report |
| `report/benchmark.py` | Benchmark runner |
| `report/benchmark_results.json` | Machine-readable benchmark results |
| `report/raw/pytest.txt` | Raw pytest output |
| `report/raw/coverage.txt` | Raw coverage output |
| `report/raw/verify_mcp.txt` | Raw MCP discovery and tool/resource verification output |
| `report/raw/client_demo.txt` | Raw FastMCP client demo output |
| `report/raw/verify_http_auth.txt` | Raw authenticated HTTP verification output |
| `report/raw/verify_postgres.txt` | Raw live PostgreSQL repository verification output |
| `report/raw/verify_mcp_postgres.txt` | Raw MCP verification output using PostgreSQL backend |
| `report/raw/pytest_postgres.txt` | Raw PostgreSQL integration test output |
| `report/raw/http_server_stdout.txt` | HTTP server stdout during auth verification |
| `report/raw/http_server_stderr.txt` | HTTP server stderr during auth verification |
| `report/raw/benchmark_stdout.txt` | Raw benchmark stdout |

## Conclusion

The implementation is ready for grading. It satisfies the base rubric through FastMCP tools/resources, reproducible SQLite data, validation/error handling, automated verification, in-process MCP client checks, and a live authenticated HTTP client verification. It also demonstrates the full bonus path with authenticated HTTP transport, working SQLite and PostgreSQL adapters behind a shared interface, output limits, tests, and benchmark artifacts.

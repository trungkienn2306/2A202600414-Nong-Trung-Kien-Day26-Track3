# Day 26 Track 3 - Real Run & Benchmark Report

Date: 2026-05-14  
Project: `2A202600414-Nong-Trung-Kien-Day26-Track3`  
Runtime: Windows 10, Python 3.12, local `.venv`  
Server: FastMCP + SQLite

## Executive Summary

The lab implementation was run locally with both in-process MCP verification and a live authenticated HTTP transport check. The FastMCP server exposes the required MCP tools and resources, SQLite data is reproducible, valid calls succeed, invalid calls return structured errors, and the authenticated HTTP transport bonus was verified.

Final status:

| Area | Result |
|---|---:|
| Pytest | 15 passed |
| Coverage | 81% |
| FastMCP tool discovery | Passed |
| MCP resource discovery | Passed |
| In-process MCP client tool/resource calls | Passed |
| Live authenticated HTTP tool/resource calls | Passed |
| Invalid request handling | Passed |
| Authenticated HTTP transport | Passed |
| Benchmark script | Passed |

## Commands Actually Run

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest --cov=src --cov-report=term-missing
.\.venv\Scripts\python.exe verify_mcp.py
.\.venv\Scripts\python.exe client_demo.py
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
15 passed in 2.60s
```

### Coverage

Result from `report/raw/coverage.txt`:

```text
TOTAL 298 statements, 58 missed, 81% coverage
15 passed in 3.80s
```

Coverage by main implementation files:

| File | Coverage |
|---|---:|
| `src/db.py` | 94% |
| `src/init_db.py` | 88% |
| `src/mcp_server.py` | 66% |
| `src/validation.py` | 89% |
| Total | 81% |

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
| `repository.search` filtered/order/limit | 100 | 0.804 | 0.617 | 2.416 | 1243.81 |
| `repository.aggregate avg(score) group_by cohort` | 100 | 1.263 | 0.935 | 2.910 | 791.48 |
| `repository.full_schema()` | 100 | 1.994 | 1.256 | 4.399 | 501.52 |
| `repository.table_schema("students")` | 100 | 0.346 | 0.281 | 0.419 | 2893.25 |
| `repository.insert` student | 30 | 6.171 | 5.813 | 8.263 | 162.06 |

Observations:

- Search and aggregate are consistently sub-2ms mean at repository level on this small dataset.
- Insert is slower because each operation performs a SQLite write transaction.
- Table schema lookup is the fastest operation.
- Full schema lookup is slower because it introspects all tables.

### MCP Client Operations

| Operation | Iterations | Mean ms | Median ms | P95 ms | Ops/sec |
|---|---:|---:|---:|---:|---:|
| `client.list_tools()` | 30 | 0.575 | 0.495 | 0.989 | 1739.89 |
| `client.read_resource("schema://database")` | 30 | 2.952 | 2.437 | 6.457 | 338.77 |
| `client.call_tool("search")` | 30 | 3.225 | 3.081 | 4.107 | 310.05 |
| `client.call_tool("aggregate")` | 30 | 3.362 | 3.327 | 4.776 | 297.41 |

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
| Server/database separation | MCP wrapper delegates to `SQLiteRepository` |
| `search` filters/order/pagination | tests + `verify_mcp.py` + benchmark |
| `insert` returns inserted payload | tests + `client_demo.py` + benchmark |
| `aggregate` count/avg/sum/min/max | tests + `client_demo.py` + benchmark |
| Full schema resource | `schema://database` verified by MCP client |
| Per-table schema template | `schema://table/students` verified by MCP client |
| Invalid table/column rejected | tests + demo invalid table |
| Unsupported operators/aggregates rejected | tests + demo bad aggregate |
| Parameterized SQL | implementation in `src/db.py`; benchmark and tests pass |
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
| SQLite + PostgreSQL shared interface | `src/repository.py` protocol and PostgreSQL boundary |
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
| `report/raw/http_server_stdout.txt` | HTTP server stdout during auth verification |
| `report/raw/http_server_stderr.txt` | HTTP server stderr during auth verification |
| `report/raw/benchmark_stdout.txt` | Raw benchmark stdout |

## Conclusion

The implementation is ready for grading. It satisfies the base rubric through FastMCP tools/resources, reproducible SQLite data, validation/error handling, automated verification, in-process MCP client checks, and a live authenticated HTTP client verification. It also demonstrates the bonus path with authenticated HTTP transport, a shared database interface, output limits, tests, and benchmark artifacts.

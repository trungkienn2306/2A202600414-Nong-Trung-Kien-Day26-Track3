from __future__ import annotations

import sqlite3
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from src.init_db import DEFAULT_DB_PATH, create_database
from src.validation import (
    SUPPORTED_OPERATORS,
    ValidationError,
    validate_column,
    validate_columns,
    validate_insert_values,
    validate_limit,
    validate_metric,
    validate_offset,
    validate_operator,
    validate_table,
)


class SQLiteRepository:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            create_database(self.db_path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def list_tables(self) -> list[str]:
        sql = "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        with self.connect() as connection:
            return [row["name"] for row in connection.execute(sql)]

    def full_schema(self) -> dict[str, list[dict[str, Any]]]:
        return {table: self.table_schema(table) for table in self.list_tables()}

    def table_schema(self, table: str) -> list[dict[str, Any]]:
        validate_table(table, self.list_tables())
        with self.connect() as connection:
            rows = connection.execute(f"PRAGMA table_info({quote_identifier(table)})").fetchall()
        return [
            {
                "cid": row["cid"],
                "name": row["name"],
                "type": row["type"],
                "not_null": bool(row["notnull"]),
                "default": row["dflt_value"],
                "primary_key": bool(row["pk"]),
            }
            for row in rows
        ]

    def column_names(self, table: str) -> list[str]:
        return [column["name"] for column in self.table_schema(table)]

    def search(
        self,
        table: str,
        filters: Any = None,
        columns: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
        order_by: str | None = None,
        descending: bool = False,
    ) -> dict[str, Any]:
        table = validate_table(table, self.list_tables())
        available_columns = self.column_names(table)
        selected_columns = validate_columns(columns, available_columns)
        where_sql, params = self._build_where(filters, available_columns)
        limit = validate_limit(limit)
        offset = validate_offset(offset)
        selected_sql = ", ".join(quote_identifier(column) for column in selected_columns)
        sql = f"SELECT {selected_sql} FROM {quote_identifier(table)}{where_sql}"
        if order_by is not None:
            order_column = validate_column(order_by, available_columns, label="order_by")
            direction = "DESC" if descending else "ASC"
            sql = f"{sql} ORDER BY {quote_identifier(order_column)} {direction}"
        sql = f"{sql} LIMIT ? OFFSET ?"
        query_params = [*params, limit, offset]
        with self.connect() as connection:
            rows = [dict(row) for row in connection.execute(sql, query_params)]
        return {
            "table": table,
            "columns": selected_columns,
            "limit": limit,
            "offset": offset,
            "count": len(rows),
            "rows": rows,
        }

    def insert(self, table: str, values: dict[str, Any]) -> dict[str, Any]:
        table = validate_table(table, self.list_tables())
        insert_values = validate_insert_values(values, self.column_names(table))
        columns = list(insert_values)
        placeholders = ", ".join("?" for _ in columns)
        column_sql = ", ".join(quote_identifier(column) for column in columns)
        sql = f"INSERT INTO {quote_identifier(table)} ({column_sql}) VALUES ({placeholders})"
        try:
            with self.connect() as connection:
                cursor = connection.execute(sql, [insert_values[column] for column in columns])
                inserted_id = cursor.lastrowid
                connection.commit()
                row = connection.execute(
                    f"SELECT * FROM {quote_identifier(table)} WHERE id = ?", (inserted_id,)
                ).fetchone()
        except sqlite3.IntegrityError as error:
            raise ValidationError("Insert violates database constraints") from error
        return {
            "table": table,
            "inserted": dict(row) if row else {**insert_values, "id": inserted_id},
        }

    def aggregate(
        self,
        table: str,
        metric: str,
        column: str | None = None,
        filters: Any = None,
        group_by: str | list[str] | None = None,
    ) -> dict[str, Any]:
        table = validate_table(table, self.list_tables())
        metric = validate_metric(metric)
        available_columns = self.column_names(table)
        aggregate_sql = self._build_aggregate_sql(table, metric, column, available_columns)
        group_columns = normalize_group_by(group_by, available_columns)
        select_parts = [quote_identifier(column_name) for column_name in group_columns]
        select_parts.append(f"{aggregate_sql} AS value")
        where_sql, params = self._build_where(filters, available_columns)
        sql = f"SELECT {', '.join(select_parts)} FROM {quote_identifier(table)}{where_sql}"
        if group_columns:
            group_sql = ", ".join(quote_identifier(column_name) for column_name in group_columns)
            sql = f"{sql} GROUP BY {group_sql} ORDER BY {group_sql}"
        with self.connect() as connection:
            rows = [dict(row) for row in connection.execute(sql, params)]
        return {
            "table": table,
            "metric": metric,
            "column": column,
            "group_by": group_columns,
            "rows": rows,
        }

    def _build_aggregate_sql(
        self, table: str, metric: str, column: str | None, available_columns: Sequence[str]
    ) -> str:
        if metric == "count" and column is None:
            return "COUNT(*)"
        if column is None:
            raise ValidationError(f"Aggregate '{metric}' requires a column")
        valid_column = validate_column(column, available_columns)
        if metric in {"avg", "sum"}:
            self._ensure_numeric(table, valid_column, metric)
        return f"{metric.upper()}({quote_identifier(valid_column)})"

    def _ensure_numeric(self, table: str, column: str, metric: str) -> None:
        column_info = next(item for item in self.table_schema(table) if item["name"] == column)
        column_type = str(column_info["type"]).upper()
        if not any(
            token in column_type for token in ("INT", "REAL", "NUM", "DEC", "FLOAT", "DOUBLE")
        ):
            raise ValidationError(
                f"Aggregate '{metric}' requires a numeric column; '{column}' is {column_type}"
            )

    def _build_where(self, filters: Any, available_columns: Sequence[str]) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        for condition in normalize_filters(filters):
            column = validate_column(condition["column"], available_columns, label="filter column")
            operator = validate_operator(condition["operator"])
            value = condition["value"]
            quoted_column = quote_identifier(column)
            if value is None and operator in {"eq", "ne"}:
                clauses.append(f"{quoted_column} IS {'NOT ' if operator == 'ne' else ''}NULL")
            elif operator == "in":
                if not isinstance(value, Sequence) or isinstance(value, str) or not value:
                    raise ValidationError("Operator 'in' requires a non-empty array value")
                placeholders = ", ".join("?" for _ in value)
                clauses.append(f"{quoted_column} IN ({placeholders})")
                params.extend(value)
            else:
                clauses.append(f"{quoted_column} {SUPPORTED_OPERATORS[operator]} ?")
                params.append(value)
        return (" WHERE " + " AND ".join(clauses), params) if clauses else ("", params)


def normalize_filters(filters: Any) -> list[dict[str, Any]]:
    if filters is None:
        return []
    if isinstance(filters, Mapping):
        normalized = []
        for column, condition in filters.items():
            if isinstance(condition, Mapping):
                normalized.append(
                    {
                        "column": column,
                        "operator": condition.get("operator", "eq"),
                        "value": condition.get("value"),
                    }
                )
            else:
                normalized.append({"column": column, "operator": "eq", "value": condition})
        return normalized
    if isinstance(filters, Sequence) and not isinstance(filters, str):
        normalized = []
        for condition in filters:
            if not isinstance(condition, Mapping):
                raise ValidationError("Each filter must be an object")
            normalized.append(
                {
                    "column": condition.get("column"),
                    "operator": condition.get("operator", "eq"),
                    "value": condition.get("value"),
                }
            )
        return normalized
    raise ValidationError("filters must be an object or an array of filter objects")


def normalize_group_by(
    group_by: str | list[str] | None, available_columns: Sequence[str]
) -> list[str]:
    if group_by is None:
        return []
    columns = [group_by] if isinstance(group_by, str) else group_by
    if not columns:
        raise ValidationError("group_by must not be empty when provided")
    return [validate_column(column, available_columns, label="group_by") for column in columns]


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'

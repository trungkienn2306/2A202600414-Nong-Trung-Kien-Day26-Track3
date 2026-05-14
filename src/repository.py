from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

import psycopg
from psycopg.rows import dict_row

from src.db import normalize_filters, normalize_group_by, quote_identifier
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


class DatabaseRepository(Protocol):
    def full_schema(self) -> dict[str, list[dict[str, Any]]]: ...

    def table_schema(self, table: str) -> list[dict[str, Any]]: ...

    def search(
        self,
        table: str,
        filters: Any = None,
        columns: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
        order_by: str | None = None,
        descending: bool = False,
    ) -> dict[str, Any]: ...

    def insert(self, table: str, values: dict[str, Any]) -> dict[str, Any]: ...

    def aggregate(
        self,
        table: str,
        metric: str,
        column: str | None = None,
        filters: Any = None,
        group_by: str | list[str] | None = None,
    ) -> dict[str, Any]: ...


class PostgresRepository:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def connect(self) -> psycopg.Connection[Any]:
        return psycopg.connect(self.dsn, row_factory=dict_row)

    def list_tables(self) -> list[str]:
        sql = """
        SELECT tablename
        FROM pg_catalog.pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename
        """
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql)
                return [row["tablename"] for row in cursor.fetchall()]

    def full_schema(self) -> dict[str, list[dict[str, Any]]]:
        return {table: self.table_schema(table) for table in self.list_tables()}

    def table_schema(self, table: str) -> list[dict[str, Any]]:
        table = validate_table(table, self.list_tables())
        sql = """
        SELECT
            columns.ordinal_position - 1 AS cid,
            columns.column_name AS name,
            columns.data_type AS type,
            columns.is_nullable = 'NO' AS not_null,
            columns.column_default AS default,
            EXISTS (
                SELECT 1
                FROM pg_index indexes
                JOIN pg_attribute attributes
                  ON attributes.attrelid = indexes.indrelid
                 AND attributes.attnum = ANY(indexes.indkey)
                WHERE indexes.indrelid = (%s)::regclass
                  AND indexes.indisprimary
                  AND attributes.attname = columns.column_name
            ) AS primary_key
        FROM information_schema.columns AS columns
        WHERE columns.table_schema = 'public' AND columns.table_name = %s
        ORDER BY columns.ordinal_position
        """
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, (qualified_table_name(table), table))
                return [dict(row) for row in cursor.fetchall()]

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
        sql = f"SELECT {selected_sql} FROM {qualified_table_name(table)}{where_sql}"
        if order_by is not None:
            order_column = validate_column(order_by, available_columns, label="order_by")
            direction = "DESC" if descending else "ASC"
            sql = f"{sql} ORDER BY {quote_identifier(order_column)} {direction}"
        sql = f"{sql} LIMIT %s OFFSET %s"
        query_params = [*params, limit, offset]
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, query_params)
                rows = [dict(row) for row in cursor.fetchall()]
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
        placeholders = ", ".join("%s" for _ in columns)
        column_sql = ", ".join(quote_identifier(column) for column in columns)
        sql = (
            f"INSERT INTO {qualified_table_name(table)} ({column_sql}) "
            f"VALUES ({placeholders}) RETURNING *"
        )
        try:
            with self.connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(sql, [insert_values[column] for column in columns])
                    row = cursor.fetchone()
                connection.commit()
        except psycopg.IntegrityError as error:
            raise ValidationError("Insert violates database constraints") from error
        return {"table": table, "inserted": dict(row) if row else insert_values}

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
        sql = f"SELECT {', '.join(select_parts)} FROM {qualified_table_name(table)}{where_sql}"
        if group_columns:
            group_sql = ", ".join(quote_identifier(column_name) for column_name in group_columns)
            sql = f"{sql} GROUP BY {group_sql} ORDER BY {group_sql}"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                rows = [dict(row) for row in cursor.fetchall()]
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
                placeholders = ", ".join("%s" for _ in value)
                clauses.append(f"{quoted_column} IN ({placeholders})")
                params.extend(value)
            else:
                clauses.append(f"{quoted_column} {SUPPORTED_OPERATORS[operator]} %s")
                params.append(value)
        return (" WHERE " + " AND ".join(clauses), params) if clauses else ("", params)


def qualified_table_name(table: str) -> str:
    return f"public.{quote_identifier(table)}"

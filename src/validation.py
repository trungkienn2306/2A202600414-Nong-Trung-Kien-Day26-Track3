from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


class ValidationError(ValueError):
    """Raised when a database request cannot be safely executed."""


SUPPORTED_OPERATORS = {
    "eq": "=",
    "ne": "!=",
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
    "like": "LIKE",
    "in": "IN",
}

SUPPORTED_AGGREGATES = {"count", "avg", "sum", "min", "max"}
MAX_LIMIT = 100


def ensure_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{name} must be an object")
    return value


def validate_table(table: str, tables: Sequence[str]) -> str:
    if table not in tables:
        allowed = ", ".join(tables)
        raise ValidationError(f"Unknown table '{table}'. Allowed tables: {allowed}")
    return table


def validate_column(column: str, columns: Sequence[str], *, label: str = "column") -> str:
    if column not in columns:
        allowed = ", ".join(columns)
        raise ValidationError(f"Unknown {label} '{column}'. Allowed columns: {allowed}")
    return column


def validate_columns(selected: Sequence[str] | None, columns: Sequence[str]) -> list[str]:
    if selected is None:
        return list(columns)
    if not selected:
        raise ValidationError("columns must not be empty when provided")
    return [validate_column(column, columns) for column in selected]


def validate_limit(limit: int) -> int:
    if not isinstance(limit, int):
        raise ValidationError("limit must be an integer")
    if limit < 1 or limit > MAX_LIMIT:
        raise ValidationError(f"limit must be between 1 and {MAX_LIMIT}")
    return limit


def validate_offset(offset: int) -> int:
    if not isinstance(offset, int):
        raise ValidationError("offset must be an integer")
    if offset < 0:
        raise ValidationError("offset must be greater than or equal to 0")
    return offset


def validate_operator(operator: str) -> str:
    if operator not in SUPPORTED_OPERATORS:
        allowed = ", ".join(SUPPORTED_OPERATORS)
        raise ValidationError(f"Unsupported operator '{operator}'. Allowed operators: {allowed}")
    return operator


def validate_metric(metric: str) -> str:
    normalized = metric.lower()
    if normalized not in SUPPORTED_AGGREGATES:
        allowed = ", ".join(sorted(SUPPORTED_AGGREGATES))
        raise ValidationError(f"Unsupported aggregate '{metric}'. Allowed aggregates: {allowed}")
    return normalized


def validate_insert_values(values: Any, columns: Sequence[str]) -> dict[str, Any]:
    mapping = ensure_mapping(values, "values")
    if not mapping:
        raise ValidationError("values must not be empty")
    return {validate_column(column, columns): value for column, value in mapping.items()}
